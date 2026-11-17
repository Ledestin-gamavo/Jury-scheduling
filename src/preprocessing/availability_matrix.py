"""Matrices de disponibilité en accès constant.

Ce module transforme les disponibilités de l'instance (dictionnaires jour →
ensemble de créneaux) en **masques plats** : pour chaque étudiant, enseignant
et salle, un ``bytearray`` de taille ``days * slots_per_day`` où la case
``day * slots_per_day + slot`` vaut ``1`` si le créneau est disponible. Une
requête « cet acteur est-il disponible à ``(day, slot)`` ? » se réduit alors
à un calcul d'indice et à une lecture : temps constant.

Le module précalcule aussi :

* les créneaux ``(jour, créneau)`` **autorisés pour chaque phase** (jours de
  ``predefence_days`` ou de ``final_defence_days``) ;
* pour chaque acteur et chaque phase, la liste triée des créneaux où il est
  disponible **et** dans la période de la phase ;
* pour chaque étudiant, la liste des **créneaux candidats** d'une phase, qui
  combine plusieurs conditions nécessaires (voir
  :meth:`AvailabilityMatrix.candidate_slots`).

Conventions :

* Un couple ``(jour, créneau)`` est représenté par :data:`TimeSlot`.
* Les indices hors de l'horizon ne lèvent pas d'exception dans les prédicats :
  ils répondent « indisponible » (``False``).
* Les entrées de disponibilité hors bornes d'une instance incohérente sont
  ignorées silencieusement ; le contrôle des bornes relève de
  :meth:`core.instance.Instance.structural_errors`.
* Une salle n'est concernée que par les finales : aucune liste de créneaux de
  salle n'est calculée pour la pré-soutenance.

Ce module ne dépend que de ``core``.
"""

from __future__ import annotations
from collections.abc import Iterable, Mapping
from typing import TypeVar
from core.enums import Availability, Phase
from core.instance import Instance

__all__ = ["TimeSlot", "AvailabilityMatrix", "group_slots_by_day"]

TimeSlot = tuple[int, int]
"""Couple ``(jour, créneau)``, indices à partir de zéro."""

_V = TypeVar("_V")


def group_slots_by_day(slots: Iterable[TimeSlot]) -> dict[int, tuple[int, ...]]:
    """Regroupe des couples ``(jour, créneau)`` par jour.

    Args:
        slots: Couples à regrouper.

    Returns:
        Dictionnaire ``jour -> créneaux`` (triés). Les jours sont triés par ordre
        croissant.
    """
    grouped: dict[int, list[int]] = {}
    for day, slot in slots:
        grouped.setdefault(day, []).append(slot)
    return {day: tuple(sorted(grouped[day])) for day in sorted(grouped)}


class AvailabilityMatrix:
    """Accès en temps constant aux disponibilités d'une instance.

    L'objet est construit une fois à partir d'une instance, puis utilisé en
    lecture seule. Le coût de construction est proportionnel à
    ``(nombre d'acteurs) × days × slots_per_day``.

    Indexation : un couple ``(day, slot)`` correspond à l'indice plat
    ``day * slots_per_day + slot`` (voir :meth:`time_index`), utile pour
    numéroter les créneaux dans un futur modèle CP-SAT.

    Exemple ::

        matrix = AvailabilityMatrix(instance)
        matrix.student_available("S01", 2, 5)           # O(1)
        matrix.is_slot_allowed(Phase.FINAL, 8, 0)       # O(1)
        matrix.candidate_slots("S01", Phase.PREDEFENCE) # liste précalculée

    Args:
        instance: Instance dont on précalcule les disponibilités.
    """

    def __init__(self, instance: Instance) -> None:
        self._instance = instance
        self._days: int = instance.days
        self._slots_per_day: int = instance.slots_per_day
        self._horizon_size: int = self._days * self._slots_per_day

        # Masques de disponibilité par acteur.
        self._student_masks: dict[str, bytearray] = {
            s.id: self._build_mask(s.availability) for s in instance.students
        }
        self._teacher_masks: dict[str, bytearray] = {
            t.id: self._build_mask(t.availability) for t in instance.teachers
        }
        self._room_masks: dict[str, bytearray] = {
            r.id: self._build_mask(r.availability) for r in instance.rooms
        }

        # Créneaux autorisés par phase.
        self._phase_masks: dict[Phase, bytearray] = {
            phase: self._build_phase_mask(phase) for phase in Phase
        }
        self._phase_indices: dict[Phase, tuple[int, ...]] = {
            phase: tuple(i for i in range(self._horizon_size) if mask[i])
            for phase, mask in self._phase_masks.items()
        }
        self._phase_time_slots: dict[Phase, tuple[TimeSlot, ...]] = {
            phase: tuple(divmod(i, self._slots_per_day) for i in indices)
            for phase, indices in self._phase_indices.items()
        }

        # Au moins une salle disponible (condition nécessaire pour une finale).
        self._any_room_mask: bytearray = self._build_any_room_mask()

        # Listes de créneaux précalculées.
        self._student_slots: dict[tuple[str, Phase], tuple[TimeSlot, ...]] = {}
        self._student_candidates: dict[tuple[str, Phase], tuple[TimeSlot, ...]] = {}
        self._teacher_slots: dict[tuple[str, Phase], tuple[TimeSlot, ...]] = {}
        self._room_slots: dict[str, tuple[TimeSlot, ...]] = {}
        self._build_slot_tables()

    # ==================================================================
    # Construction (privée)
    # ==================================================================
    def _build_mask(self, availability: Availability) -> bytearray:
        """Convertit une :class:`Availability` en masque plat.

        Les entrées hors de l'horizon sont ignorées.
        """
        mask = bytearray(self._horizon_size)
        spd = self._slots_per_day
        for day, slots in availability.slots_by_day.items():
            if not 0 <= day < self._days:
                continue
            base = day * spd
            for slot in slots:
                if 0 <= slot < spd:
                    mask[base + slot] = 1
        return mask

    def _build_phase_mask(self, phase: Phase) -> bytearray:
        """Construit le masque des créneaux autorisés pour une phase."""
        mask = bytearray(self._horizon_size)
        spd = self._slots_per_day
        for day in self._instance.days_for_phase(phase):
            if 0 <= day < self._days:
                base = day * spd
                mask[base : base + spd] = b"\x01" * spd
        return mask

    def _build_any_room_mask(self) -> bytearray:
        """Construit le masque « au moins une salle disponible »."""
        mask = bytearray(self._horizon_size)
        for room_mask in self._room_masks.values():
            for i in range(self._horizon_size):
                if room_mask[i]:
                    mask[i] = 1
        return mask

    def _intersect(self, phase: Phase, *masks: bytearray) -> tuple[TimeSlot, ...]:
        """Retourne les créneaux de ``phase`` où tous les masques valent 1."""
        spd = self._slots_per_day
        return tuple(
            divmod(i, spd)
            for i in self._phase_indices[phase]
            if all(mask[i] for mask in masks)
        )

    def _build_slot_tables(self) -> None:
        """Remplit les tables de créneaux par acteur et par phase."""
        for student in self._instance.students:
            mask = self._student_masks[student.id]
            supervisor_mask = self._teacher_masks.get(student.supervisor_id)
            for phase in Phase:
                key = (student.id, phase)
                self._student_slots[key] = self._intersect(phase, mask)
                if not student.requires_phase(phase):
                    self._student_candidates[key] = ()
                elif phase is Phase.PREDEFENCE:
                    self._student_candidates[key] = self._student_slots[key]
                elif supervisor_mask is None:
                    self._student_candidates[key] = ()
                else:
                    self._student_candidates[key] = self._intersect(
                        phase, mask, supervisor_mask, self._any_room_mask
                    )
        for teacher in self._instance.teachers:
            mask = self._teacher_masks[teacher.id]
            for phase in Phase:
                self._teacher_slots[(teacher.id, phase)] = self._intersect(phase, mask)
        for room in self._instance.rooms:
            self._room_slots[room.id] = self._intersect(Phase.FINAL, self._room_masks[room.id])

    @staticmethod
    def _require(table: Mapping[str, _V], kind: str, identifier: str) -> _V:
        """Retourne ``table[identifier]`` ou lève un ``KeyError`` explicite."""
        try:
            return table[identifier]
        except KeyError:
            raise KeyError(f"{kind} inconnu : {identifier!r}") from None

    def _flat(self, day: int, slot: int) -> int:
        """Retourne l'indice plat d'un créneau, ou ``-1`` s'il est hors horizon."""
        if 0 <= day < self._days and 0 <= slot < self._slots_per_day:
            return day * self._slots_per_day + slot
        return -1

    # ==================================================================
    # Horizon et indexation
    # ==================================================================
    @property
    def instance(self) -> Instance:
        """Instance d'origine."""
        return self._instance

    @property
    def horizon_size(self) -> int:
        """Nombre total de couples ``(jour, créneau)`` de l'horizon."""
        return self._horizon_size

    def is_valid_time_slot(self, day: int, slot: int) -> bool:
        """Indique si ``(day, slot)`` appartient à l'horizon de l'instance."""
        return self._flat(day, slot) >= 0

    def time_index(self, day: int, slot: int) -> int:
        """Retourne l'indice plat ``day * slots_per_day + slot``.

        Raises:
            ValueError: Si le couple est hors de l'horizon.
        """
        index = self._flat(day, slot)
        if index < 0:
            raise ValueError(
                f"Créneau hors horizon : (jour={day}, créneau={slot}) pour "
                f"{self._days} jours × {self._slots_per_day} créneaux"
            )
        return index

    def time_slot_from_index(self, index: int) -> TimeSlot:
        """Retourne le couple ``(jour, créneau)`` d'un indice plat.

        Raises:
            ValueError: Si l'indice est hors de ``[0, horizon_size)``.
        """
        if not 0 <= index < self._horizon_size:
            raise ValueError(f"Indice de créneau hors horizon : {index}")
        day, slot = divmod(index, self._slots_per_day)
        return (day, slot)

    # Prédicats en temps constant
    def student_available(self, student_id: str, day: int, slot: int) -> bool:
        """Indique si l'étudiant est disponible à ``(day, slot)``.

        Raises:
            KeyError: Si l'étudiant est inconnu.
        """
        mask = self._require(self._student_masks, "Étudiant", student_id)
        index = self._flat(day, slot)
        return index >= 0 and mask[index] == 1

    def teacher_available(self, teacher_id: str, day: int, slot: int) -> bool:
        """Indique si l'enseignant est disponible à ``(day, slot)``.

        Raises:
            KeyError: Si l'enseignant est inconnu.
        """
        mask = self._require(self._teacher_masks, "Enseignant", teacher_id)
        index = self._flat(day, slot)
        return index >= 0 and mask[index] == 1

    def room_available(self, room_id: str, day: int, slot: int) -> bool:
        """Indique si la salle est disponible à ``(day, slot)``.

        La disponibilité d'une salle ne concerne que les finales ; ce prédicat
        ne tient pas compte de la phase.

        Raises:
            KeyError: Si la salle est inconnue.
        """
        mask = self._require(self._room_masks, "Salle", room_id)
        index = self._flat(day, slot)
        return index >= 0 and mask[index] == 1

    def any_room_available(self, day: int, slot: int) -> bool:
        """Indique si au moins une salle est disponible à ``(day, slot)``."""
        index = self._flat(day, slot)
        return index >= 0 and self._any_room_mask[index] == 1

    def is_slot_allowed(self, phase: Phase, day: int, slot: int) -> bool:
        """Indique si le créneau appartient à la période commune de ``phase``.

        Un créneau est autorisé pour une phase si son jour figure dans
        ``predefence_days`` (pré-soutenance) ou ``final_defence_days`` (finale)
        et si le créneau appartient à l'horizon.
        """
        index = self._flat(day, slot)
        return index >= 0 and self._phase_masks[phase][index] == 1

    # Listes de créneaux précalculées
    def phase_time_slots(self, phase: Phase) -> tuple[TimeSlot, ...]:
        """Retourne tous les créneaux autorisés pour une phase, triés."""
        return self._phase_time_slots[phase]

    def student_slots(self, student_id: str, phase: Phase) -> tuple[TimeSlot, ...]:
        """Retourne les créneaux où l'étudiant est disponible dans la période de ``phase``.

        Ne tient compte que de l'étudiant et de la période de la phase.

        Raises:
            KeyError: Si l'étudiant est inconnu.
        """
        self._require(self._student_masks, "Étudiant", student_id)
        return self._student_slots[(student_id, phase)]

    def teacher_slots(self, teacher_id: str, phase: Phase) -> tuple[TimeSlot, ...]:
        """Retourne les créneaux où l'enseignant est disponible dans la période de ``phase``.

        Raises:
            KeyError: Si l'enseignant est inconnu.
        """
        self._require(self._teacher_masks, "Enseignant", teacher_id)
        return self._teacher_slots[(teacher_id, phase)]

    def room_slots(self, room_id: str) -> tuple[TimeSlot, ...]:
        """Retourne les créneaux où la salle est disponible dans la période des finales.

        Raises:
            KeyError: Si la salle est inconnue.
        """
        self._require(self._room_masks, "Salle", room_id)
        return self._room_slots[room_id]

    def candidate_slots(self, student_id: str, phase: Phase) -> tuple[TimeSlot, ...]:
        """Retourne les créneaux candidats d'un étudiant pour une phase.

        Ce sont les créneaux qui satisfont les **conditions nécessaires**
        suivantes, toutes issues du contrat :

        * l'étudiant est disponible ;
        * le créneau appartient à la période de la phase ;
        * pour une **finale** : l'encadrant (rapporteur obligatoire) est
          disponible et au moins une salle est disponible.

        Ce sont des conditions nécessaires, non suffisantes : le jury, la
        disponibilité d'une salle précise, les plafonds journaliers et les
        non-chevauchements restent à traiter par le solveur.

        Si l'étudiant ne doit pas passer cette phase (finale d'un étudiant non
        admissible), la liste est vide.

        Raises:
            KeyError: Si l'étudiant est inconnu.
        """
        self._require(self._student_masks, "Étudiant", student_id)
        return self._student_candidates[(student_id, phase)]

    def candidate_slots_by_day(
        self, student_id: str, phase: Phase
    ) -> dict[int, tuple[int, ...]]:
        """Retourne :meth:`candidate_slots` regroupés par jour."""
        return group_slots_by_day(self.candidate_slots(student_id, phase))

    def common_slots(
        self, phase: Phase, student_id: str, teacher_ids: Iterable[str]
    ) -> tuple[TimeSlot, ...]:
        """Retourne les créneaux de ``phase`` communs à un étudiant et des enseignants.

        Un créneau est retenu s'il est dans la période de la phase et si
        l'étudiant et **tous** les enseignants indiqués y sont disponibles.
        Les salles ne sont pas prises en compte. Coût : proportionnel au nombre
        de créneaux de la phase.

        Args:
            phase: Phase concernée.
            student_id: Identifiant de l'étudiant.
            teacher_ids: Enseignants devant être présents.

        Raises:
            KeyError: Si l'étudiant ou un enseignant est inconnu.
        """
        masks = [self._require(self._student_masks, "Étudiant", student_id)]
        masks.extend(self._require(self._teacher_masks, "Enseignant", t) for t in teacher_ids)
        return self._intersect(phase, *masks)

    def teachers_available_at(self, day: int, slot: int) -> tuple[str, ...]:
        """Retourne les enseignants disponibles à ``(day, slot)``, dans l'ordre de l'instance.

        Coût : proportionnel au nombre d'enseignants.
        """
        index = self._flat(day, slot)
        if index < 0:
            return ()
        return tuple(tid for tid, mask in self._teacher_masks.items() if mask[index])

    def rooms_available_at(self, day: int, slot: int) -> tuple[str, ...]:
        """Retourne les salles disponibles à ``(day, slot)``, dans l'ordre de l'instance.

        Coût : proportionnel au nombre de salles.
        """
        index = self._flat(day, slot)
        if index < 0:
            return ()
        return tuple(rid for rid, mask in self._room_masks.items() if mask[index])