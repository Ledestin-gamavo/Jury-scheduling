"""Réparation locale d'un planning par éviction et réinsertion.

Le :class:`RepairOperator` corrige un planning présentant des violations
simples (conflit de salle, conflit d'enseignant, dépassement de plafond,
jury incohérent, séance manquante…) **sans métaheuristique** : uniquement des
corrections locales, au niveau d'un étudiant.

Principe, en trois temps.

1. **Conservation.** Les étudiants sont parcourus dans l'ordre d'apparition
   dans la solution. Le plan d'un étudiant (sa pré-soutenance et, s'il est
   admissible, sa finale avec le **même** binôme) est conservé seulement si
   chacune de ses séances respecte toutes les contraintes dures vis-à-vis des
   étudiants déjà conservés (:meth:`SessionBuilder.check_session`). Sinon
   l'étudiant est mis **en attente**, avec toutes ses séances. Un conflit est
   ainsi toujours résolu au détriment de la séance la plus tardive. Les séances
   d'étudiants inconnus sont abandonnées.
2. **Réinsertion.** Chaque étudiant en attente est replanifié en entier
   (:meth:`SessionBuilder.build_student`), du plus contraint au moins contraint
   (MRV). Replanifier l'étudiant en entier lui permet de changer de binôme.
3. **Éviction bornée.** S'il reste des étudiants en attente, au plus
   ``max_repair_iterations`` tours sont effectués. À chaque tour, quelques
   étudiants déjà placés sont évincés : d'abord ceux qui partagent l'encadrant
   d'un étudiant en attente (l'encadrant est imposé à la finale), puis ceux qui
   partagent un enseignant avec ses binômes possibles. Les étudiants en attente
   sont alors replanifiés en premier. Un tour qui laisse **plus** d'étudiants en
   attente que le meilleur état connu est annulé (l'état est restauré). Les
   choix aléatoires sont pilotés par ``config.random_seed`` : le résultat est
   reproductible.

Le module est léger : il réutilise les contrôles et la construction de
:mod:`solvers.greedy.session_builder` et ne duplique aucune règle.
"""

from __future__ import annotations

from dataclasses import dataclass
from random import Random

from core.enums import Phase
from core.instance import Instance
from core.session import Session
from core.solution import Solution
from core.student import Student
from preprocessing import PreprocessingContext, build_preprocessing

from .greedy_config import GreedyConfig
from .session_builder import ScheduleState, SessionBuilder

__all__ = ["RepairResult", "RepairOperator"]


@dataclass(frozen=True)
class RepairResult:
    """Résultat d'une réparation.

    Attributes:
        solution: Planning réparé (ne contient que des étudiants entièrement planifiés).
        unplaced_students: Étudiants qui n'ont pas pu être replanifiés.
        iterations: Nombre de tours d'éviction-réinsertion effectués.
        initial_unplaced: Nombre d'étudiants en attente avant toute réinsertion.
        evicted_students: Nombre total d'évictions effectuées pendant les tours.
    """

    solution: Solution
    unplaced_students: tuple[str, ...]
    iterations: int
    initial_unplaced: int
    evicted_students: int

    @property
    def complete(self) -> bool:
        """Vrai si tous les étudiants sont planifiés."""
        return not self.unplaced_students


class RepairOperator:
    """Opérateur de réparation locale (éviction et réinsertion).

    Args:
        config: Configuration du solveur (graine, nombre de tours, taille d'éviction,
            poids du guidage). Configuration par défaut si absente.
    """

    def __init__(self, config: GreedyConfig | None = None) -> None:
        self._config = config if config is not None else GreedyConfig()

    @property
    def config(self) -> GreedyConfig:
        """Configuration utilisée."""
        return self._config

    def repair(
        self,
        instance: Instance,
        solution: Solution,
        *,
        context: PreprocessingContext | None = None,
    ) -> RepairResult:
        """Répare un planning.

        La solution fournie n'est jamais modifiée : un nouveau planning est
        construit.

        Args:
            instance: Instance du problème.
            solution: Planning à réparer (complet ou non, valide ou non).
            context: Contexte de pré-traitement déjà construit (facultatif ;
                construit avec filtrage des enseignants sans disponibilité si absent).

        Returns:
            Le résultat de réparation.

        Raises:
            ValueError: Si ``context`` ne correspond pas à ``instance``.
        """
        if context is None:
            context = build_preprocessing(instance, prune_unavailable_teachers=True)
        elif context.instance is not instance and context.instance.instance_id != instance.instance_id:
            raise ValueError("Le contexte de pré-traitement ne correspond pas à l'instance")

        rng = Random(self._config.random_seed)
        builder = SessionBuilder(context, self._config, rng)
        state = ScheduleState(instance, context.availability)

        pending = self._keep_consistent_students(instance, builder, state, solution)
        initial_unplaced = len(pending)
        pending = self._insert(builder, state, builder.mrv_order(pending))

        best_sessions = state.snapshot()
        best_pending = list(pending)
        iterations = 0
        evicted = 0
        while (
            pending
            and iterations < self._config.max_repair_iterations
            and self._config.repair_eviction_size > 0
        ):
            iterations += 1
            victims = self._choose_victims(instance, builder, state, pending, rng)
            if not victims:
                break
            for student_id in victims:
                state.remove_student(student_id)
            evicted += len(victims)
            order = builder.mrv_order(pending) + builder.mrv_order(victims)
            pending = self._insert(builder, state, order)
            if len(pending) <= len(best_pending):
                best_sessions = state.snapshot()
                best_pending = list(pending)
            else:
                state.restore(best_sessions)
                pending = list(best_pending)

        return RepairResult(
            solution=state.to_solution(),
            unplaced_students=tuple(pending),
            iterations=iterations,
            initial_unplaced=initial_unplaced,
            evicted_students=evicted,
        )

    # ==================================================================
    # Étapes internes
    # ==================================================================
    @staticmethod
    def _plan_of(student: Student, sessions: list[Session]) -> tuple[Session, ...] | None:
        """Retourne le plan complet d'un étudiant, ou ``None`` s'il est incohérent.

        Un plan est cohérent s'il contient exactement une pré-soutenance et, pour
        un étudiant admissible, exactement une finale de même binôme ; aucune
        finale pour un étudiant non admissible.
        """
        predefences = [s for s in sessions if s.phase is Phase.PREDEFENCE]
        finals = [s for s in sessions if s.phase is Phase.FINAL]
        if len(predefences) != 1:
            return None
        if student.eligible_final:
            if len(finals) != 1 or finals[0].jury_pair != predefences[0].jury_pair:
                return None
            return (predefences[0], finals[0])
        if finals:
            return None
        return (predefences[0],)

    def _keep_consistent_students(
        self,
        instance: Instance,
        builder: SessionBuilder,
        state: ScheduleState,
        solution: Solution,
    ) -> list[str]:
        """Conserve les plans cohérents et retourne les étudiants mis en attente."""
        by_student: dict[str, list[Session]] = {}
        for session in solution.sessions:
            if instance.has_student(session.student_id):
                by_student.setdefault(session.student_id, []).append(session)
        order = list(by_student) + [sid for sid in instance.student_ids if sid not in by_student]

        pending: list[str] = []
        for student_id in order:
            plan = self._plan_of(instance.student(student_id), by_student.get(student_id, []))
            if plan is None:
                pending.append(student_id)
                continue
            placed: list[Session] = []
            consistent = True
            for session in plan:
                if builder.check_session(state, session):
                    consistent = False
                    break
                state.add(session)
                placed.append(session)
            if not consistent:
                for session in placed:
                    state.remove(session)
                pending.append(student_id)
        return pending

    @staticmethod
    def _insert(builder: SessionBuilder, state: ScheduleState, order: list[str]) -> list[str]:
        """Replanifie les étudiants dans l'ordre donné ; retourne ceux qui échouent."""
        failed: list[str] = []
        for student_id in order:
            plan = builder.build_student(state, student_id)
            if plan is None:
                failed.append(student_id)
                continue
            for session in plan:
                state.add(session)
        return failed

    def _choose_victims(
        self,
        instance: Instance,
        builder: SessionBuilder,
        state: ScheduleState,
        pending: list[str],
        rng: Random,
    ) -> list[str]:
        """Choisit les étudiants placés à évincer pour faire de la place.

        Pour chaque étudiant en attente, jusqu'à ``repair_eviction_size`` étudiants
        placés sont tirés : d'abord parmi ceux qui ont le même encadrant, puis
        parmi ceux qui partagent un enseignant (encadrant ou membre du jury) avec
        les binômes possibles de l'étudiant en attente, enfin parmi tous les
        étudiants placés si aucun n'est lié.
        """
        size = self._config.repair_eviction_size
        planned = [sid for sid in instance.student_ids if state.has_student(sid)]
        if not planned:
            return []

        teachers_of: dict[str, set[str]] = {}
        for student_id in planned:
            members = {instance.student(student_id).supervisor_id}
            predefence = state.session_of(student_id, Phase.PREDEFENCE)
            if predefence is not None:
                members.update(predefence.jury_pair)
            teachers_of[student_id] = members

        chosen: dict[str, None] = {}
        for student_id in pending:
            supervisor = instance.student(student_id).supervisor_id
            related = {supervisor}
            for pair in builder.jury.pairs_for(student_id):
                related.update(pair)
            remaining = [sid for sid in planned if sid not in chosen]
            primary = [sid for sid in remaining if instance.student(sid).supervisor_id == supervisor]
            secondary = [
                sid
                for sid in remaining
                if instance.student(sid).supervisor_id != supervisor and teachers_of[sid] & related
            ]
            picked = rng.sample(primary, min(size, len(primary)))
            if len(picked) < size:
                picked += rng.sample(secondary, min(size - len(picked), len(secondary)))
            if not picked:
                picked = rng.sample(remaining, min(size, len(remaining)))
            chosen.update(dict.fromkeys(picked))
        return list(chosen)