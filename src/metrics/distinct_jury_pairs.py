"""Métrique 5 : ``distinct_jury_pairs``.

Définition (contrat v4.0) : nombre de couples **ordonnés**
``(president_id, examiner_id)`` distincts affectés aux étudiants, **comptés une
seule fois à partir de la pré-soutenance** de chaque étudiant. Minimiser cette
valeur encourage la réutilisation des mêmes binômes entre étudiants, quels que
soient les jours, les créneaux ou les salles.

Hypothèses retenues :

* **H1. Source du comptage.** Seules les pré-soutenances sont lues, comme
  l'impose le contrat. Tout étudiant en ayant exactement une (contrainte dure),
  chaque étudiant contribue par un binôme. La continuité du jury étant
  obligatoire pour les étudiants admissibles, le binôme de la finale est
  identique : lire aussi les finales ne changerait rien sur une solution
  valide, mais pourrait fausser le compte sur une solution invalide.
* **H2. Couples ordonnés.** ``(A, B)`` et ``(B, A)`` sont deux couples
  différents : le président est toujours le premier élément.
* **H3.** Ce critère est distinct de la contrainte de continuité entre les
  phases (voir le module ``validation``).
* **H4.** Une solution sans pré-soutenance donne 0.

Dépend uniquement de ``core``.
"""

from __future__ import annotations
from collections.abc import Sequence

from core.enums import Phase
from core.instance import Instance
from core.session import Session
from core.solution import Solution

from .teacher_presence_days import as_session_sequence

__all__ = ["jury_pairs", "distinct_jury_pairs"]


def jury_pairs(
    instance: Instance, solution: Solution | Sequence[Session]
) -> frozenset[tuple[str, str]]:
    """Retourne l'ensemble des binômes ``(président, examinateur)`` distincts.

    Seules les pré-soutenances sont lues (hypothèse H1). Cet ensemble est utile
    pour diagnostiquer quels binômes sont utilisés.

    Args:
        instance: Instance du problème (non utilisée dans le calcul ; conservée
            pour l'uniformité de signature des métriques).
        solution: Solution **valide** (ou séquence de séances).

    Returns:
        L'ensemble des couples ordonnés distincts.
    """
    return frozenset(
        session.jury_pair
        for session in as_session_sequence(solution)
        if session.phase is Phase.PREDEFENCE
    )


def distinct_jury_pairs(
    instance: Instance, solution: Solution | Sequence[Session]
) -> int:
    """Calcule le nombre de binômes (président, examinateur) distincts.

    Exemple : si trois étudiants ont les jurys ``(T1, T2)``, ``(T1, T2)`` et
    ``(T3, T2)``, le score vaut 2.

    Args:
        instance: Instance du problème.
        solution: Solution **valide** (ou séquence de séances).

    Returns:
        Le score (entier >= 0, à minimiser).
    """
    return len(jury_pairs(instance, solution))