"""Classement des candidats du ``GreedySolver``.

Ce module ordonne les choix possibles du solveur, du meilleur au moins bon :

* :func:`rank_jury_pairs` : binômes ``(président, examinateur)`` ;
* :func:`rank_time_slots` : créneaux ``(jour, créneau)`` ;
* :func:`rank_rooms` : salles d'une finale.

Principe. Chaque candidat reçoit un **coût estimé** : la variation locale que
son choix provoquerait sur les critères du contrat, calculée de façon
incrémentale à partir de l'état d'occupation courant (aucune réévaluation
complète du planning). Les critères pris en compte :

* ``teacher_presence_days`` : +1 pour chaque participant convoqué un jour où il
  n'a encore aucune séance ;
* ``teacher_idle_slots`` : variation exacte du nombre de créneaux creux de chaque
  participant ce jour-là (négative si le créneau comble un trou) ;
* ``supervisor_group_breaks`` : variation exacte de ``max(0, groupes - 1)`` pour
  l'encadrant de l'étudiant, avec la définition de groupe du contrat (créneaux
  distincts consécutifs en ligne ; séances adjacentes de même encadrant dans
  une même salle en finale) ;
* ``distinct_jury_pairs`` : un binôme jamais utilisé coûte plus cher ;
* ``teacher_load_range`` : approchée par la charge cumulée des membres du
  binôme (privilégier les moins chargés tire l'équilibre).

Le coût total est une somme pondérée (poids de :class:`GreedyConfig`). Les
égalités sont départagées par le générateur pseudo-aléatoire fourni (donc de
façon reproductible), ou par l'ordre naturel si aucun générateur n'est donné.

Si ``config.use_candidate_ordering`` est faux, chaque fonction retourne les
candidats dans leur ordre d'origine (*first-fit*).

Les fonctions sont pures vis-à-vis de l'état : elles le lisent sans le modifier.
Leur seule action de bord est de consommer le générateur pseudo-aléatoire.
"""

from __future__ import annotations

from collections.abc import Collection, Sequence
from random import Random
from typing import TYPE_CHECKING, TypeVar

from core.enums import Phase
from core.student import Student
from preprocessing import Pair, TimeSlot

from .greedy_config import GreedyConfig

if TYPE_CHECKING:  # évite l'import circulaire avec session_builder
    from .session_builder import ScheduleState

__all__ = [
    "idle_delta",
    "breaks_delta",
    "rank_jury_pairs",
    "rank_time_slots",
    "rank_rooms",
]

_T = TypeVar("_T")


def idle_delta(occupied: Collection[int], slot: int) -> int:
    """Calcule la variation des créneaux creux d'un enseignant pour un jour.

    Les créneaux creux d'un jour valent ``dernier - premier + 1 - nombre de
    séances``. Cette fonction retourne la variation si l'on ajoute ``slot`` aux
    créneaux déjà occupés ``occupied`` de ce jour.

    Args:
        occupied: Créneaux déjà occupés par l'enseignant ce jour-là.
        slot: Créneau que l'on envisage d'ajouter.

    Returns:
        La variation (entier, négatif si le créneau comble un trou, nul si le
        jour est vide ou si le créneau est déjà occupé).
    """
    if not occupied or slot in occupied:
        return 0
    low, high = min(occupied), max(occupied)
    before = high - low + 1 - len(occupied)
    after = max(high, slot) - min(low, slot) + 1 - (len(occupied) + 1)
    return after - before


def breaks_delta(current_groups: int, groups_delta: int) -> int:
    """Calcule la variation de ``max(0, groupes - 1)`` après un changement de groupes.

    Args:
        current_groups: Nombre actuel de groupes de l'encadrant (sur tous les jours).
        groups_delta: Variation du nombre de groupes (+1, 0 ou -1).

    Returns:
        La variation du nombre de ruptures de l'encadrant.
    """
    return max(0, current_groups + groups_delta - 1) - max(0, current_groups - 1)


def _ranked(items: Sequence[_T], costs: Sequence[float], rng: Random | None) -> list[_T]:
    """Trie ``items`` par coût croissant ; égalités départagées par ``rng``.

    Sans générateur, le tri étant stable, les égalités conservent l'ordre
    d'origine.
    """
    if rng is None:
        order = sorted(range(len(items)), key=costs.__getitem__)
    else:
        keys = [(cost, rng.random()) for cost in costs]
        order = sorted(range(len(items)), key=keys.__getitem__)
    return [items[index] for index in order]


def rank_jury_pairs(
    state: ScheduleState,
    pairs: Sequence[Pair],
    config: GreedyConfig,
    rng: Random | None = None,
) -> list[Pair]:
    """Classe les binômes ``(président, examinateur)`` du meilleur au moins bon.

    Coût d'un binôme : ``weight_new_jury_pair`` s'il n'a encore été utilisé par
    aucune pré-soutenance, plus ``weight_teacher_load`` fois la somme des
    charges actuelles de ses deux membres. Réutiliser un binôme réduit
    ``distinct_jury_pairs`` ; préférer les enseignants peu chargés réduit
    ``teacher_load_range``. Le compromis entre les deux est réglé par les poids.

    Args:
        state: État d'occupation courant.
        pairs: Binômes candidats (déjà conformes aux rôles et au domaine).
        config: Configuration du solveur.
        rng: Générateur pour départager les égalités (facultatif).

    Returns:
        Les binômes classés (nouvelle liste ; ``pairs`` n'est pas modifié).
    """
    if not config.use_candidate_ordering or len(pairs) < 2:
        return list(pairs)
    costs = [
        (0.0 if state.pair_used(pair) else config.weight_new_jury_pair)
        + config.weight_teacher_load * (state.load(pair[0]) + state.load(pair[1]))
        for pair in pairs
    ]
    return _ranked(pairs, costs, rng)


def rank_time_slots(
    state: ScheduleState,
    student: Student,
    phase: Phase,
    pair: Pair,
    slots: Sequence[TimeSlot],
    config: GreedyConfig,
    rng: Random | None = None,
) -> list[TimeSlot]:
    """Classe les créneaux candidats d'une séance du meilleur au moins bon.

    Participants pris en compte pour la présence et les créneaux creux :
    président et examinateur ; plus l'encadrant de l'étudiant pour une finale.
    Pour une finale, le terme de regroupement de l'encadrant retient la
    meilleure salle libre du créneau (le choix de la salle est ensuite fait par
    :func:`rank_rooms`).

    Les créneaux fournis doivent déjà satisfaire les contraintes dures (c'est le
    rôle de :class:`~solvers.greedy.session_builder.SessionBuilder`) ; cette
    fonction ne fait que les ordonner.

    Args:
        state: État d'occupation courant.
        student: Étudiant concerné.
        phase: Phase de la séance.
        pair: Binôme ``(président, examinateur)`` retenu.
        slots: Créneaux candidats ``(jour, créneau)``.
        config: Configuration du solveur.
        rng: Générateur pour départager les égalités (facultatif).

    Returns:
        Les créneaux classés (nouvelle liste).
    """
    if not config.use_candidate_ordering or len(slots) < 2:
        return list(slots)

    supervisor = student.supervisor_id
    president, examiner = pair
    online = phase is Phase.PREDEFENCE
    attendees = (president, examiner) if online else (president, examiner, supervisor)
    groups = state.online_group_count(supervisor) if online else state.final_group_count(supervisor)

    costs: list[float] = []
    for day, slot in slots:
        presence = sum(1 for teacher in attendees if state.teacher_day_count(teacher, day) == 0)
        idle = sum(idle_delta(state.teacher_day_slots(teacher, day), slot) for teacher in attendees)
        if online:
            group_delta = state.online_group_delta(supervisor, day, slot)
        else:
            group_delta = min(
                (
                    state.final_group_delta(supervisor, day, room, slot)
                    for room in state.free_rooms(day, slot)
                ),
                default=1,
            )
        costs.append(
            config.weight_presence_days * presence
            + config.weight_idle_slots * idle
            + config.weight_group_breaks * breaks_delta(groups, group_delta)
        )
    return _ranked(slots, costs, rng)


def rank_rooms(
    state: ScheduleState,
    student: Student,
    day: int,
    slot: int,
    rooms: Sequence[str],
    config: GreedyConfig,
    rng: Random | None = None,
) -> list[str]:
    """Classe les salles libres d'une finale du meilleur au moins bon.

    Seul le regroupement des séances de l'encadrant dépend de la salle : une
    salle où la séance prolonge un groupe de même encadrant (créneau adjacent)
    est préférée, car elle n'ajoute pas de rupture. La capacité des salles
    n'est pas une donnée du projet et n'intervient donc pas.

    Args:
        state: État d'occupation courant.
        student: Étudiant de la finale.
        day: Jour de la finale.
        slot: Créneau de la finale.
        rooms: Salles libres candidates (déjà conformes aux contraintes dures).
        config: Configuration du solveur.
        rng: Générateur pour départager les égalités (facultatif).

    Returns:
        Les salles classées (nouvelle liste).
    """
    if not config.use_candidate_ordering or len(rooms) < 2:
        return list(rooms)
    supervisor = student.supervisor_id
    groups = state.final_group_count(supervisor)
    costs = [
        config.weight_group_breaks
        * breaks_delta(groups, state.final_group_delta(supervisor, day, room, slot))
        for room in rooms
    ]
    return _ranked(rooms, costs, rng)