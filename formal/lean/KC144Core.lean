import Init

namespace KC144Core

theorem bool_and_assoc (a b c : Bool) :
    (a && (b && c)) = ((a && b) && c) := by
  cases a <;> cases b <;> cases c <;> rfl

theorem bool_or_assoc (a b c : Bool) :
    (a || (b || c)) = ((a || b) || c) := by
  cases a <;> cases b <;> cases c <;> rfl

theorem bool_complement (a : Bool) :
    (a && (!a)) = false ∧ (a || (!a)) = true := by
  cases a <;> decide

theorem crt_instance :
    (8 % 3 = 2) ∧ (8 % 5 = 3) := by
  decide

structure Mat2 (α : Type) where
  a00 : α
  a01 : α
  a10 : α
  a11 : α

def Mat2.transpose {α : Type} (A : Mat2 α) : Mat2 α :=
  ⟨A.a00, A.a10, A.a01, A.a11⟩

theorem transpose_involution {α : Type} (A : Mat2 α) :
    A.transpose.transpose = A := by
  cases A
  rfl

end KC144Core
