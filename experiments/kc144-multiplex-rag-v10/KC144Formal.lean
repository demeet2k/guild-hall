import Mathlib

open scoped BigOperators

namespace KC144MultiplexRAG

theorem complex_polar_multiplication (r ρ θ φ : ℝ) :
    ((r : ℂ) * Complex.exp ((θ : ℂ) * Complex.I)) *
        ((ρ : ℂ) * Complex.exp ((φ : ℂ) * Complex.I)) =
      ((r * ρ : ℝ) : ℂ) * Complex.exp (((θ + φ : ℝ) : ℂ) * Complex.I) := by
  rw [show ((θ + φ : ℝ) : ℂ) * Complex.I =
      (θ : ℂ) * Complex.I + (φ : ℂ) * Complex.I by push_cast; ring]
  rw [Complex.exp_add]
  push_cast
  ring

theorem finite_orthogonal_projection {n : ℕ} (a : Fin n → ℂ) (k : Fin n) :
    (∑ i, a i * (if i = k then 1 else 0)) = a k := by
  simp

theorem standard_basis_projection {n : ℕ} (v : Fin n → ℝ) (k : Fin n) :
    (∑ i, v i * (if i = k then 1 else 0)) = v k := by
  simp

end KC144MultiplexRAG
