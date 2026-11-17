"""Métrique 4 : ``supervisor_group_breaks``.

Mesure les **ruptures** des blocs de soutenances d'un même encadrant : plus les
séances des étudiants d'un même encadrant sont regroupées dans le temps, plus le
score est faible. L'encadrant n'a pas besoin d'assister aux pré-soutenances en
ligne : le critère est organisationnel (convention de modélisation, pas une
règle institutionnelle).

Définition (contrat v4.0), calculée séparément pour chaque phase.

**Pré-soutenances en ligne.** Pour chaque couple (encadrant, jour) :

1. on collecte les créneaux **distincts** occupés par les étudiants de cet
   encadrant ce jour-là (des séances simultanées d'étudiants d'un même
   encadrant ne comptent que pour un seul créneau : aucune salle ni ordre
   fictif entre passages simultanés) ;
2. un **groupe** est une suite maximale de créneaux consécutifs
   (``c, c+1, c+2, ...``) ;
3. les séances d'autres encadrants n'interrompent pas une suite.

**Finales.** Pour chaque couple (jour, salle), les séances sont triées par
``(créneau, student_id)``. Un groupe est une suite maximale de séances
**temporellement adjacentes** de même encadrant.

**Agrégation.** Pour chaque couple (encadrant, phase), on additionne les groupes
sur tous les jours (et toutes les salles pour les finales), puis on retient
``max(0, nombre_de_groupes - 1)``. Le score est la somme de ces contributions.

Hypothèses retenues :

* **H1. Adjacence en finale.** Deux séances triées successives d'une même salle
  et d'un même jour appartiennent au même groupe si elles ont le même
  encadrant **et** des créneaux consécutifs (``créneau + 1``). Un créneau vide
  entre deux séances du même encadrant coupe le groupe : « adjacentes »
  s'entend comme « immédiatement adjacentes », et un trou n'est pas adjacent.
  Cette lecture suit la formulation du dictionnaire de données (« suite de
  séances immédiatement adjacentes, dans la même salle et le même jour »). Elle
  est isolée dans :func:`_count_final_groups` pour pouvoir être modifiée si la
  lecture du validateur officiel diffère ; le validateur officiel fait foi.
* **H2.** L'encadrant d'un étudiant est ``student.supervisor_id`` (une seule
  personne, aussi rapporteur).
* **H3.** Un encadrant dont les séances forment un seul groupe (par phase)
  contribue pour 0, tout comme un encadrant sans séance. Les deux phases
  contribuent séparément : un encadrant ayant un seul bloc en ligne et un seul
  bloc en finale a un score de 0.
* **H4.** Le calcul est déterministe : l'ordre des séances dans la solution n'a
  aucune influence sur le résultat (tri explicite, regroupement par clés).
* **H5.** Dans une solution valide, deux finales ne partagent ni le même
  créneau ni la même salle. Si c'était le cas (solution invalide), les deux
  séances au même créneau ne sont jamais adjacentes : elles ouvrent chacune un
  groupe, de façon déterministe.

Dépend uniquement de ``core``.
"""

from __future__ import annotations
from collections import defaultdict
from collections.abc import Sequence

from core.enums import Phase
from core.instance import Instance
from core.session import Session
from core.solution import Solution

from .teacher_presence_days import MetricsInputError, as_session_sequence

__all__ = [
    "supervisor_group_counts",
    "supervisor_group_breaks_by_phase",
    "supervisor_group_breaks",
]


def _supervisor_of(instance: Instance, session: Session) -> str:
    """Retourne l'encadrant de l'étudiant d'une séance.

    Raises:
        MetricsInputError: Si l'étudiant est inconnu.
    """
    if not instance.has_student(session.student_id):
        raise MetricsInputError(
            f"Étudiant inconnu {session.student_id!r} : les métriques exigent une solution valide"
        )
    return instance.student(session.student_id).supervisor_id


def _count_consecutive_runs(slots: Sequence[int]) -> int:
    """Compte les suites maximales de créneaux consécutifs.

    Args:
        slots: Créneaux **distincts et triés** par ordre croissant.

    Returns:
        Le nombre de groupes (0 si la séquence est vide).
    """
    runs = 0
    previous: int | None = None
    for slot in slots:
        if previous is None or slot != previous + 1:
            runs += 1
        previous = slot
    return runs


def _count_online_groups(
    instance: Instance, sessions: Sequence[Session]
) -> dict[str, int]:
    """Compte, par encadrant, les groupes de pré-soutenances en ligne.

    Les créneaux distincts de chaque couple (encadrant, jour) sont regroupés en
    suites de créneaux consécutifs ; les groupes sont additionnés sur les jours.
    """
    occupied: dict[tuple[str, int], set[int]] = defaultdict(set)
    for session in sessions:
        if session.phase is Phase.PREDEFENCE:
            occupied[(_supervisor_of(instance, session), session.day)].add(session.slot)
    groups: dict[str, int] = defaultdict(int)
    for (supervisor_id, _day), slots in occupied.items():
        groups[supervisor_id] += _count_consecutive_runs(sorted(slots))
    return dict(groups)


def _count_final_groups(
    instance: Instance, sessions: Sequence[Session]
) -> dict[str, int]:
    """Compte, par encadrant, les groupes de finales (hypothèse H1).

    Les finales sont regroupées par (jour, salle) et triées par
    ``(créneau, student_id)``. Une nouvelle séance prolonge le groupe courant si
    son encadrant est le même que celui de la séance précédente et si son
    créneau suit immédiatement (``+ 1``) ; sinon elle ouvre un nouveau groupe.
    """
    by_room_day: dict[tuple[int, str | None], list[Session]] = defaultdict(list)
    for session in sessions:
        if session.phase is Phase.FINAL:
            by_room_day[(session.day, session.room_id)].append(session)

    groups: dict[str, int] = defaultdict(int)
    for key in sorted(by_room_day, key=lambda k: (k[0], k[1] or "")):
        ordered = sorted(by_room_day[key], key=lambda s: (s.slot, s.student_id))
        previous_supervisor: str | None = None
        previous_slot: int | None = None
        for session in ordered:
            supervisor_id = _supervisor_of(instance, session)
            continues = (
                previous_supervisor == supervisor_id
                and previous_slot is not None
                and session.slot == previous_slot + 1
            )
            if not continues:
                groups[supervisor_id] += 1
            previous_supervisor = supervisor_id
            previous_slot = session.slot
    return dict(groups)


def supervisor_group_counts(
    instance: Instance, solution: Solution | Sequence[Session], phase: Phase
) -> dict[str, int]:
    """Retourne le nombre de groupes de chaque encadrant pour une phase.

    Seuls les encadrants ayant au moins une séance dans la phase figurent dans
    le résultat. Cette fonction détaille le calcul de la métrique et sert aux
    rapports ou aux diagnostics.

    Args:
        instance: Instance du problème.
        solution: Solution **valide** (ou séquence de séances).
        phase: Phase à analyser.

    Returns:
        Table ``identifiant d'encadrant -> nombre de groupes`` (trié par encadrant).

    Raises:
        MetricsInputError: Si une séance référence un étudiant inconnu.
    """
    sessions = as_session_sequence(solution)
    if phase is Phase.PREDEFENCE:
        counts = _count_online_groups(instance, sessions)
    else:
        counts = _count_final_groups(instance, sessions)
    return dict(sorted(counts.items()))


def supervisor_group_breaks_by_phase(
    instance: Instance, solution: Solution | Sequence[Session]
) -> dict[Phase, int]:
    """Retourne la contribution de chaque phase à la métrique.

    Pour chaque phase, somme sur les encadrants de ``max(0, groupes - 1)``. La
    somme des deux valeurs est exactement :func:`supervisor_group_breaks`.

    Args:
        instance: Instance du problème.
        solution: Solution **valide** (ou séquence de séances).

    Returns:
        Table ``phase -> contribution`` (les deux phases sont toujours présentes).

    Raises:
        MetricsInputError: Si une séance référence un étudiant inconnu.
    """
    return {
        phase: sum(
            max(0, count - 1)
            for count in supervisor_group_counts(instance, solution, phase).values()
        )
        for phase in Phase
    }


def supervisor_group_breaks(
    instance: Instance, solution: Solution | Sequence[Session]
) -> int:
    """Calcule le nombre total de ruptures de groupes d'encadrants.

    Somme, sur les encadrants et sur les deux phases, de
    ``max(0, nombre_de_groupes - 1)``. Voir la documentation du module pour la
    définition exacte des groupes et les hypothèses retenues.

    Args:
        instance: Instance du problème.
        solution: Solution **valide** (ou séquence de séances).

    Returns:
        Le score (entier >= 0, à minimiser).

    Raises:
        MetricsInputError: Si une séance référence un étudiant inconnu.
    """
    return sum(supervisor_group_breaks_by_phase(instance, solution).values())