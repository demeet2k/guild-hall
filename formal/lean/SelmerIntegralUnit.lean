import Mathlib

namespace KC144SelmerIntegralUnit

def normResidue (a b c : Nat) : Nat :=
  a^3 + 6*b^3 + 36*c^3 + 54*a*b*c

theorem p2_residue_obstruction :
    ∀ a b c : Fin 8,
      (3*a.val) % 2 = 0 →
      (3*a.val^2 + 2*b.val*c.val) % 4 = 0 →
      normResidue a.val b.val c.val % 8 = 0 →
      a.val % 2 = 0 ∧ b.val % 2 = 0 ∧ c.val % 2 = 0 := by
  native_decide

theorem p3_residue_obstruction :
    ∀ a b c : Fin 27,
      (3*a.val^2) % 9 = 0 →
      normResidue a.val b.val c.val % 27 = 0 →
      a.val % 3 = 0 ∧ b.val % 3 = 0 ∧ c.val % 3 = 0 := by
  native_decide

structure CubicElt where
  a : ℤ
  b : ℤ
  c : ℤ
deriving DecidableEq, Repr

def mul (x y : CubicElt) : CubicElt :=
  ⟨x.a*y.a + 6*(x.b*y.c + x.c*y.b),
   x.a*y.b + x.b*y.a + 6*x.c*y.c,
   x.a*y.c + x.b*y.b + x.c*y.a⟩

def one : CubicElt := ⟨1,0,0⟩
def u : CubicElt := ⟨1,-6,3⟩
def epsilon : CubicElt := ⟨109,60,33⟩
def pow3 (x : CubicElt) : CubicElt := mul (mul x x) x

theorem unit_inverse : mul u epsilon = one := by
  native_decide

theorem principal_element_relations :
    pow3 ⟨2,-1,0⟩ = mul ⟨2,0,0⟩ u ∧
    pow3 ⟨3,2,1⟩ = mul ⟨3,0,0⟩ epsilon ∧
    mul (mul ⟨-5,1,1⟩ ⟨7,-2,-1⟩) ⟨1,1,0⟩ =
      mul ⟨7,0,0⟩ u := by
  native_decide

end KC144SelmerIntegralUnit
