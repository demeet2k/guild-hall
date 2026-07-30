From Coq Require Import Bool.Bool Arith.Arith Arith.PeanoNat ZArith.ZArith.
From Coq Require Import Lists.List Lia Ring.
Import ListNotations.
Open Scope Z_scope.

Module KC144Safe.

Theorem bool_and_assoc : forall a b c : bool,
  andb a (andb b c) = andb (andb a b) c.
Proof. intros [] [] []; reflexivity. Qed.

Theorem bool_or_assoc : forall a b c : bool,
  orb a (orb b c) = orb (orb a b) c.
Proof. intros [] [] []; reflexivity. Qed.

Theorem bool_complement : forall a : bool,
  andb a (negb a) = false /\ orb a (negb a) = true.
Proof. intros []; simpl; auto. Qed.

Theorem finite_forall_three : forall b0 b1 b2 : bool,
  forallb (fun x => x) [b0;b1;b2] = andb b0 (andb b1 b2).
Proof. intros [] [] []; reflexivity. Qed.

Theorem finite_exists_three : forall b0 b1 b2 : bool,
  existsb (fun x => x) [b0;b1;b2] = orb b0 (orb b1 b2).
Proof. intros [] [] []; reflexivity. Qed.

Theorem gcd_update_48_18 :
  Nat.gcd 48 18 = Nat.gcd 18 (48 mod 18).
Proof. vm_compute. reflexivity. Qed.

Definition legendre7 (a : nat) : Z :=
  if Nat.eqb (a mod 7) 0 then 0
  else if existsb (Nat.eqb (a mod 7)) [1%nat;2%nat;4%nat]
       then 1 else -1.

Theorem legendre7_instance :
  legendre7 ((3*5) mod 7) = (legendre7 3 * legendre7 5)%Z.
Proof. vm_compute. reflexivity. Qed.

Theorem mobius_sum_six :
  (1 + (-1) + (-1) + 1)%Z = 0%Z.
Proof. ring. Qed.

Theorem hadamard_convolution_n2 :
  forall x0 x1 y0 y1 : Z,
  (x0*y0 + x1*y1) + (x0*y1 + x1*y0) =
  (x0+x1)*(y0+y1).
Proof. intros; ring. Qed.

Theorem crt_2_mod3_3_mod5 :
  (Z.modulo 8 3 = 2 /\ Z.modulo 8 5 = 3)%Z.
Proof. vm_compute. auto. Qed.

Record Mat2 (A : Type) := mkMat2 {
  a00 : A; a01 : A; a10 : A; a11 : A
}.

Arguments mkMat2 {A}.
Arguments a00 {A}.
Arguments a01 {A}.
Arguments a10 {A}.
Arguments a11 {A}.

Definition transpose {A : Type} (M : Mat2 A) : Mat2 A :=
  mkMat2 (a00 M) (a10 M) (a01 M) (a11 M).

Theorem transpose_transpose :
  forall (A : Type) (M : Mat2 A), transpose (transpose M) = M.
Proof. intros A [x00 x01 x10 x11]; reflexivity. Qed.

Theorem cayley_hamilton_2x2 :
  forall a b c d : Z,
    a*a + b*c - (a+d)*a + (a*d-b*c) = 0 /\
    a*b + b*d - (a+d)*b = 0 /\
    c*a + d*c - (a+d)*c = 0 /\
    c*b + d*d - (a+d)*d + (a*d-b*c) = 0.
Proof. intros; repeat split; ring. Qed.

Theorem polynomial_chain_rule_instance :
  forall x : Z, 2*(x*x+1)*(2*x) = 4*x*(x*x+1).
Proof. intros; ring. Qed.

End KC144Safe.
