"""Candidats de jury précalculés, partagés entre étudiants équivalents.

Pour chaque étudiant, ce module précalcule :

* les **présidents** possibles ;
* les **examinateurs** possibles ;
* les **binômes** ordonnés ``(président, examinateur)`` possibles.

Règles du contrat prises en compte :

* le président a le rôle ``president`` (aucune condition de domaine) ;
* l'examinateur a le rôle ``examiner`` et couvre le domaine de l'étudiant ;
* le président et l'examinateur sont deux personnes **distinctes** ;
* le binôme choisi à la pré-soutenance reste le même à la finale (continuité).
  Pour un étudiant **admissible à la finale**, les trois membres du jury final
  (président, examinateur, encadrant-rapporteur) doivent être distincts : ni le
  président ni l'examinateur ne peuvent donc être l'encadrant de l'étudiant.
  Pour un étudiant non admissible, aucune finale n'a lieu et cette exclusion ne
  s'applique pas.

Partage des calculs : les candidats ne dépendent que de la clé
``(domaine, encadrant exclu ou None)``. Tous les étudiants ayant la même clé
partagent **le même objet** de candidats ; ils sont calculés une seule fois. Le
nombre de groupes distincts est donné par :attr:`JuryCandidates.num_groups`.

Filtrage facultatif par disponibilité : si ``prune_unavailable=True`` (avec une
:class:`~preprocessing.availability_matrix.AvailabilityMatrix`), un enseignant
n'ayant **aucun** créneau disponible dans la période d'une phase requise est
écarté. C'est une condition nécessaire, jamais suffisante.

Les listes sont déterministes : elles suivent l'ordre des enseignants dans
l'instance. L'indice d'un binôme dans :meth:`JuryCandidates.pairs_for` est donc
stable, ce qui sert à numéroter les variables d'un futur modèle CP-SAT.

Ce module ne dépend que de ``core`` et des autres modules de ``preprocessing``.
"""

from __future__ import annotations
from collections.abc import Mapping
from dataclasses import dataclass
from functools import cached_property
from types import MappingProxyType
from core.enums import Phase
from core.instance import Instance
from .availability_matrix import AvailabilityMatrix, TimeSlot
from .domain_filters import DomainFilters

__all__ = ["Pair", "JuryCandidatesSummary", "JuryCandidates"]

Pair = tuple[str, str]
"""Binôme ordonné ``(president_id, examiner_id)``."""

_GroupKey = tuple[str, str | None]
"""Clé de partage : ``(domaine, encadrant exclu ou None)``."""


@dataclass(frozen=True)
class JuryCandidatesSummary:
    """Résumé des candidats de jury d'une instance.

    Attributes:
        num_students: Nombre d'étudiants.
        num_groups: Nombre de groupes distincts de candidats (calculs réellement faits).
        num_distinct_pairs: Nombre de binômes distincts utilisables par au moins un étudiant.
        total_pair_candidates: Somme, sur les étudiants, du nombre de binômes possibles.
        min_pairs_per_student: Minimum de binômes possibles pour un étudiant.
        max_pairs_per_student: Maximum de binômes possibles pour un étudiant.
        mean_pairs_per_student: Moyenne de binômes possibles par étudiant.
        students_without_candidates: Étudiants sans aucun binôme possible
            (indice d'instance non résolvable).
    """

    num_students: int
    num_groups: int
    num_distinct_pairs: int
    total_pair_candidates: int
    min_pairs_per_student: int
    max_pairs_per_student: int
    mean_pairs_per_student: float
    students_without_candidates: tuple[str, ...]


@dataclass(frozen=True)
class _CandidateGroup:
    """Candidats partagés par tous les étudiants d'une même clé (usage interne)."""

    presidents: tuple[str, ...]
    examiners: tuple[str, ...]
    pairs: tuple[Pair, ...]
    pair_index: Mapping[Pair, int]


class JuryCandidates:
    """Présidents, examinateurs et binômes possibles pour chaque étudiant.

    Exemple ::

        jury = JuryCandidates(instance)
        jury.pairs_for("S01")                         # tuple de (président, examinateur)
        jury.is_pair_allowed("S01", "T01", "T05")     # O(1)
        jury.students_for_pair(("T01", "T05"))        # étudiants pouvant l'utiliser

    Note : :meth:`presidents_for` et :meth:`examiners_for` listent les
    candidats **par rôle** ; la faisabilité conjointe (personnes distinctes) est
    portée par :meth:`pairs_for`.

    Args:
        instance: Instance du problème.
        domain_filters: Filtres de domaine déjà construits (réutilisés pour
            éviter un recalcul). Construits si absents.
        availability: Matrice de disponibilités (facultative). Requise pour
            :meth:`pair_slots` et pour ``prune_unavailable``.
        prune_unavailable: Si vrai, écarte les enseignants sans aucun créneau
            disponible dans la période d'une phase requise.

    Raises:
        ValueError: Si ``prune_unavailable`` est vrai sans ``availability``.
    """

    def __init__(
        self,
        instance: Instance,
        *,
        domain_filters: DomainFilters | None = None,
        availability: AvailabilityMatrix | None = None,
        prune_unavailable: bool = False,
    ) -> None:
        if prune_unavailable and availability is None:
            raise ValueError("prune_unavailable=True nécessite une AvailabilityMatrix")
        self._instance = instance
        self._filters = domain_filters if domain_filters is not None else DomainFilters(instance)
        self._availability = availability
        self._prune = prune_unavailable
        self._usable_cache: dict[tuple[str, bool], bool] = {}

        self._student_key: dict[str, _GroupKey] = {}
        students_by_key: dict[_GroupKey, list[str]] = {}
        for student in instance.students:
            excluded = student.supervisor_id if student.eligible_final else None
            key: _GroupKey = (student.domain, excluded)
            self._student_key[student.id] = key
            students_by_key.setdefault(key, []).append(student.id)
        self._students_by_key: dict[_GroupKey, tuple[str, ...]] = {
            k: tuple(v) for k, v in students_by_key.items()
        }
        self._groups: dict[_GroupKey, _CandidateGroup] = {
            key: self._build_group(key) for key in self._students_by_key
        }

    # Construction (privée)
    def _is_usable(self, teacher_id: str, final_needed: bool) -> bool:
        """Indique si l'enseignant a des créneaux dans les périodes requises.

        Toujours vrai si le filtrage par disponibilité est désactivé.
        """
        if not self._prune or self._availability is None:
            return True
        cache_key = (teacher_id, final_needed)
        cached = self._usable_cache.get(cache_key)
        if cached is None:
            cached = bool(self._availability.teacher_slots(teacher_id, Phase.PREDEFENCE)) and (
                not final_needed or bool(self._availability.teacher_slots(teacher_id, Phase.FINAL))
            )
            self._usable_cache[cache_key] = cached
        return cached

    def _build_group(self, key: _GroupKey) -> _CandidateGroup:
        """Calcule les candidats d'une clé ``(domaine, encadrant exclu)``."""
        domain, excluded = key
        final_needed = excluded is not None
        presidents = tuple(
            tid
            for tid in self._filters.presidents()
            if tid != excluded and self._is_usable(tid, final_needed)
        )
        examiners = tuple(
            tid
            for tid in self._filters.examiners_for_domain(domain)
            if tid != excluded and self._is_usable(tid, final_needed)
        )
        pairs = tuple((p, e) for p in presidents for e in examiners if p != e)
        pair_index = MappingProxyType({pair: i for i, pair in enumerate(pairs)})
        return _CandidateGroup(presidents, examiners, pairs, pair_index)

    def _group(self, student_id: str) -> _CandidateGroup:
        """Retourne le groupe de candidats d'un étudiant."""
        try:
            return self._groups[self._student_key[student_id]]
        except KeyError:
            raise KeyError(f"Étudiant inconnu : {student_id!r}") from None

    # Candidats par étudiant
    def presidents_for(self, student_id: str) -> tuple[str, ...]:
        """Retourne les présidents possibles pour l'étudiant (par rôle).

        Pour un étudiant admissible à la finale, son encadrant est exclu.

        Raises:
            KeyError: Si l'étudiant est inconnu.
        """
        return self._group(student_id).presidents

    def examiners_for(self, student_id: str) -> tuple[str, ...]:
        """Retourne les examinateurs possibles pour l'étudiant (rôle et domaine).

        Pour un étudiant admissible à la finale, son encadrant est exclu.

        Raises:
            KeyError: Si l'étudiant est inconnu.
        """
        return self._group(student_id).examiners

    def pairs_for(self, student_id: str) -> tuple[Pair, ...]:
        """Retourne les binômes ``(président, examinateur)`` possibles.

        Les deux membres sont distincts. L'ordre est déterministe (ordre des
        enseignants dans l'instance, président en premier) et l'indice d'un
        binôme dans ce tuple est stable.

        Raises:
            KeyError: Si l'étudiant est inconnu.
        """
        return self._group(student_id).pairs

    def pair_index_for(self, student_id: str) -> Mapping[Pair, int]:
        """Retourne la table en lecture seule ``binôme -> indice`` dans :meth:`pairs_for`.

        Raises:
            KeyError: Si l'étudiant est inconnu.
        """
        return self._group(student_id).pair_index

    def num_pairs(self, student_id: str) -> int:
        """Retourne le nombre de binômes possibles pour l'étudiant."""
        return len(self._group(student_id).pairs)

    def has_candidates(self, student_id: str) -> bool:
        """Indique si l'étudiant a au moins un binôme possible."""
        return bool(self._group(student_id).pairs)

    def is_pair_allowed(self, student_id: str, president_id: str, examiner_id: str) -> bool:
        """Indique, en temps constant, si le binôme est possible pour l'étudiant.

        Raises:
            KeyError: Si l'étudiant est inconnu.
        """
        return (president_id, examiner_id) in self._group(student_id).pair_index

    def students_without_candidates(self) -> tuple[str, ...]:
        """Retourne les étudiants sans aucun binôme possible (dans l'ordre de l'instance)."""
        return tuple(
            sid for sid in self._instance.student_ids if not self._group(sid).pairs
        )

    # Vue globale
    @property
    def num_groups(self) -> int:
        """Nombre de groupes distincts de candidats (un calcul par groupe)."""
        return len(self._groups)

    @cached_property
    def _teacher_order(self) -> dict[str, int]:
        """Position de chaque enseignant dans l'instance."""
        return {tid: i for i, tid in enumerate(self._instance.teacher_ids)}

    @cached_property
    def _all_pairs(self) -> tuple[Pair, ...]:
        """Union triée des binômes de tous les groupes."""
        union: set[Pair] = set()
        for group in self._groups.values():
            union.update(group.pairs)
        order = self._teacher_order
        return tuple(sorted(union, key=lambda pair: (order[pair[0]], order[pair[1]])))

    @cached_property
    def _global_pair_index(self) -> dict[Pair, int]:
        """Indice global de chaque binôme dans :meth:`all_pairs`."""
        return {pair: i for i, pair in enumerate(self._all_pairs)}

    @cached_property
    def _students_by_pair(self) -> dict[Pair, tuple[str, ...]]:
        """Étudiants pouvant utiliser chaque binôme, dans l'ordre de l'instance."""
        position = {sid: i for i, sid in enumerate(self._instance.student_ids)}
        collected: dict[Pair, list[str]] = {}
        for key, group in self._groups.items():
            members = self._students_by_key[key]
            for pair in group.pairs:
                collected.setdefault(pair, []).extend(members)
        return {
            pair: tuple(sorted(members, key=position.__getitem__))
            for pair, members in collected.items()
        }

    def all_pairs(self) -> tuple[Pair, ...]:
        """Retourne tous les binômes utilisables par au moins un étudiant.

        Triés par position du président puis de l'examinateur dans l'instance.
        Utile pour modéliser le critère ``distinct_jury_pairs``.
        """
        return self._all_pairs

    def global_pair_index(self, pair: Pair) -> int:
        """Retourne l'indice du binôme dans :meth:`all_pairs`.

        Raises:
            KeyError: Si le binôme n'est utilisable par aucun étudiant.
        """
        try:
            return self._global_pair_index[pair]
        except KeyError:
            raise KeyError(f"Binôme inconnu ou inutilisable : {pair!r}") from None

    def students_for_pair(self, pair: Pair) -> tuple[str, ...]:
        """Retourne les étudiants pouvant utiliser ce binôme (vide s'il est inconnu)."""
        return self._students_by_pair.get(pair, ())

    # Créneaux communs d'un binôme
    def pair_slots(
        self, student_id: str, president_id: str, examiner_id: str, phase: Phase
    ) -> tuple[TimeSlot, ...]:
        """Retourne les créneaux de ``phase`` où tout le jury et l'étudiant sont disponibles.

        Participants pris en compte : étudiant, président, examinateur, et en
        finale l'encadrant (rapporteur). Les salles ne sont pas considérées ;
        les plafonds journaliers et non-chevauchements non plus.

        Raises:
            ValueError: Si le module a été construit sans matrice de disponibilités.
            KeyError: Si un identifiant est inconnu.
        """
        if self._availability is None:
            raise ValueError("pair_slots nécessite une AvailabilityMatrix")
        teacher_ids = [president_id, examiner_id]
        if phase is Phase.FINAL:
            teacher_ids.append(self._instance.student(student_id).supervisor_id)
        return self._availability.common_slots(phase, student_id, teacher_ids)

    # Résumé
    def summary(self) -> JuryCandidatesSummary:
        """Retourne un résumé statistique des candidats de jury."""
        counts = [self.num_pairs(sid) for sid in self._instance.student_ids]
        total = sum(counts)
        return JuryCandidatesSummary(
            num_students=len(counts),
            num_groups=self.num_groups,
            num_distinct_pairs=len(self._all_pairs),
            total_pair_candidates=total,
            min_pairs_per_student=min(counts) if counts else 0,
            max_pairs_per_student=max(counts) if counts else 0,
            mean_pairs_per_student=(total / len(counts)) if counts else 0.0,
            students_without_candidates=self.students_without_candidates(),
        )