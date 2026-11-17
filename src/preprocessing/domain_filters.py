"""Filtres précalculés liés aux domaines scientifiques.

Ce module répond en temps constant (ou par simple lecture d'un tuple déjà
construit) aux questions de type :

* quels enseignants couvrent le domaine ``D`` ?
* quels enseignants peuvent être **examinateurs** pour ``D`` (rôle ``examiner``
  et domaine couvert) ?
* quels enseignants peuvent être **présidents** (rôle ``president``, sans
  condition de domaine) ?
* quels étudiants appartiennent à ``D`` ? quels encadrants ont des étudiants
  dans ``D`` ?
* combien d'examinateurs par étudiant dans ``D`` (statistiques de domaine) ?

Règles du contrat reprises ici : l'examinateur doit avoir le rôle ``examiner``
**et** couvrir le domaine de l'étudiant ; le président doit avoir le rôle
``president`` et n'a aucune obligation de domaine.

Conventions de retour :

* les collections retournées sont des tuples d'**identifiants**, dans l'ordre de
  l'instance (déterministe) ;
* pour un domaine inconnu, les requêtes de liste retournent un tuple vide et les
  prédicats retournent ``False`` ;
* pour un enseignant ou un étudiant inconnu, les méthodes qui doivent
  retrouver l'objet lèvent ``KeyError``.

Ce module ne dépend que de ``core``.
"""

from __future__ import annotations
from dataclasses import dataclass
from core.enums import Role
from core.instance import Instance

__all__ = ["DomainStatistics", "DomainFilters"]

@dataclass(frozen=True)
class DomainStatistics:
    """Statistiques d'un domaine scientifique.

    Attributes:
        domain: Identifiant du domaine.
        num_students: Nombre d'étudiants du domaine.
        num_final_students: Nombre d'étudiants du domaine admissibles à la finale.
        num_supervisors: Nombre d'encadrants distincts ayant des étudiants dans le domaine.
        num_teachers_covering: Nombre d'enseignants couvrant le domaine (tous rôles).
        num_examiners: Nombre d'enseignants pouvant examiner le domaine.
        num_covering_presidents: Nombre d'enseignants habilités présidents qui
            couvrent aussi le domaine (information seulement : un président
            n'a pas à couvrir le domaine).
        examiners_per_student: Rapport ``num_examiners / num_students``, ou
            ``None`` si le domaine n'a aucun étudiant.
    """

    domain: str
    num_students: int
    num_final_students: int
    num_supervisors: int
    num_teachers_covering: int
    num_examiners: int
    num_covering_presidents: int
    examiners_per_student: float | None


class DomainFilters:
    """Index des enseignants, examinateurs, présidents et étudiants par domaine.

    Construit une fois à partir d'une instance ; en lecture seule ensuite.

    Exemple ::

        filters = DomainFilters(instance)
        filters.examiners_for_domain("IA")         # tuple d'identifiants
        filters.can_examine("T03", "IA")            # O(1)
        filters.domains_without_examiner()          # diagnostic d'infaisabilité

    Args:
        instance: Instance dont on précalcule les filtres.
    """

    def __init__(self, instance: Instance) -> None:
        self._instance = instance

        covering: dict[str, list[str]] = {d: [] for d in instance.domains}
        examiners: dict[str, list[str]] = {d: [] for d in instance.domains}
        students: dict[str, list[str]] = {d: [] for d in instance.domains}
        final_students: dict[str, int] = {d: 0 for d in instance.domains}
        supervisors: dict[str, list[str]] = {d: [] for d in instance.domains}

        for teacher in instance.teachers:
            for domain in sorted(teacher.domains):
                covering.setdefault(domain, []).append(teacher.id)
                if teacher.can_examine(domain):
                    examiners.setdefault(domain, []).append(teacher.id)

        self._student_domain: dict[str, str] = {}
        for student in instance.students:
            self._student_domain[student.id] = student.domain
            students.setdefault(student.domain, []).append(student.id)
            final_students.setdefault(student.domain, 0)
            if student.eligible_final:
                final_students[student.domain] += 1
            domain_supervisors = supervisors.setdefault(student.domain, [])
            if student.supervisor_id not in domain_supervisors:
                domain_supervisors.append(student.supervisor_id)

        for domain in list(covering):
            examiners.setdefault(domain, [])
            students.setdefault(domain, [])
            supervisors.setdefault(domain, [])
            final_students.setdefault(domain, 0)
        for domain in list(students):
            covering.setdefault(domain, [])
            examiners.setdefault(domain, [])
            supervisors.setdefault(domain, [])
            final_students.setdefault(domain, 0)

        self._domains: tuple[str, ...] = tuple(covering)
        self._covering: dict[str, tuple[str, ...]] = {d: tuple(v) for d, v in covering.items()}
        self._examiners: dict[str, tuple[str, ...]] = {d: tuple(v) for d, v in examiners.items()}
        self._examiner_sets: dict[str, frozenset[str]] = {
            d: frozenset(v) for d, v in examiners.items()
        }
        self._students: dict[str, tuple[str, ...]] = {d: tuple(v) for d, v in students.items()}
        self._supervisors: dict[str, tuple[str, ...]] = {
            d: tuple(v) for d, v in supervisors.items()
        }
        self._presidents: tuple[str, ...] = tuple(t.id for t in instance.eligible_presidents())
        self._president_set: frozenset[str] = frozenset(self._presidents)
        self._teacher_domains: dict[str, frozenset[str]] = {
            t.id: t.domains for t in instance.teachers
        }

        self._statistics: dict[str, DomainStatistics] = {}
        for domain in self._domains:
            num_students = len(self._students[domain])
            num_examiners = len(self._examiners[domain])
            self._statistics[domain] = DomainStatistics(
                domain=domain,
                num_students=num_students,
                num_final_students=final_students[domain],
                num_supervisors=len(self._supervisors[domain]),
                num_teachers_covering=len(self._covering[domain]),
                num_examiners=num_examiners,
                num_covering_presidents=sum(
                    1 for tid in self._covering[domain] if tid in self._president_set
                ),
                examiners_per_student=(num_examiners / num_students if num_students else None),
            )

    # Domaines
    @property
    def domains(self) -> tuple[str, ...]:
        """Domaines de l'instance, suivis d'éventuels domaines inconnus référencés.

        Dans une instance cohérente, ce sont exactement ``instance.domains``.
        """
        return self._domains

    # Enseignants
    def teachers_covering(self, domain: str) -> tuple[str, ...]:
        """Retourne les enseignants couvrant ``domain``, tous rôles confondus."""
        return self._covering.get(domain, ())

    def examiners_for_domain(self, domain: str) -> tuple[str, ...]:
        """Retourne les enseignants pouvant être examinateurs pour ``domain``.

        Condition : rôle ``examiner`` **et** couverture du domaine.
        """
        return self._examiners.get(domain, ())

    def presidents(self) -> tuple[str, ...]:
        """Retourne les enseignants habilités comme présidents.

        Aucune condition de domaine ne s'applique au président.
        """
        return self._presidents

    def examiners_for_student(self, student_id: str) -> tuple[str, ...]:
        """Retourne les examinateurs possibles pour le domaine d'un étudiant.

        Raises:
            KeyError: Si l'étudiant est inconnu.
        """
        try:
            domain = self._student_domain[student_id]
        except KeyError:
            raise KeyError(f"Étudiant inconnu : {student_id!r}") from None
        return self._examiners.get(domain, ())

    def domains_of_teacher(self, teacher_id: str) -> frozenset[str]:
        """Retourne les domaines couverts par un enseignant.

        Raises:
            KeyError: Si l'enseignant est inconnu.
        """
        try:
            return self._teacher_domains[teacher_id]
        except KeyError:
            raise KeyError(f"Enseignant inconnu : {teacher_id!r}") from None

    def covers(self, teacher_id: str, domain: str) -> bool:
        """Indique, en temps constant, si l'enseignant couvre ``domain``.

        Retourne ``False`` pour un enseignant inconnu.
        """
        return domain in self._teacher_domains.get(teacher_id, frozenset())

    def can_examine(self, teacher_id: str, domain: str) -> bool:
        """Indique, en temps constant, si l'enseignant peut examiner ``domain``.

        Retourne ``False`` pour un enseignant ou un domaine inconnu.
        """
        return teacher_id in self._examiner_sets.get(domain, frozenset())

    def can_preside(self, teacher_id: str) -> bool:
        """Indique, en temps constant, si l'enseignant est habilité comme président."""
        return teacher_id in self._president_set

    # Étudiants et encadrants
    def students_in_domain(self, domain: str) -> tuple[str, ...]:
        """Retourne les étudiants d'un domaine, dans l'ordre de l'instance."""
        return self._students.get(domain, ())

    def supervisors_in_domain(self, domain: str) -> tuple[str, ...]:
        """Retourne les encadrants distincts ayant des étudiants dans ``domain``."""
        return self._supervisors.get(domain, ())

    # Statistiques et diagnostics
    def statistics(self, domain: str) -> DomainStatistics:
        """Retourne les statistiques d'un domaine.

        Raises:
            KeyError: Si le domaine est inconnu.
        """
        try:
            return self._statistics[domain]
        except KeyError:
            raise KeyError(f"Domaine inconnu : {domain!r}") from None

    def all_statistics(self) -> tuple[DomainStatistics, ...]:
        """Retourne les statistiques de tous les domaines, dans l'ordre de :attr:`domains`."""
        return tuple(self._statistics[d] for d in self._domains)

    def domains_without_examiner(self) -> tuple[str, ...]:
        """Retourne les domaines ayant des étudiants mais aucun examinateur possible.

        Une instance qui en possède ne peut pas être résolue : c'est un
        diagnostic précoce utile avant toute résolution.
        """
        return tuple(
            d for d in self._domains if self._students[d] and not self._examiners[d]
        )

    @property
    def num_presidents(self) -> int:
        """Nombre d'enseignants habilités comme présidents."""
        return len(self._presidents)

    @staticmethod
    def role_for_domain_rule(role: Role) -> bool:
        """Indique si le rôle est soumis à la correspondance de domaine.

        Seul l'examinateur doit couvrir le domaine de l'étudiant (contrat v4.0).
        """
        return role is Role.EXAMINER