# Quest Board

This document tracks active quests (tasks) for the Manscript ‑ Being and Athena projects.  Each quest includes a description, rationale and acceptance criteria.  Contributors can claim quests by opening a GitHub issue referencing the quest ID.

## Quest 1 – Align method signatures
**Description:** Unify the method signatures for updating entities and networks.  Currently `Entity.update` accepts a time delta `dt` while `ManualEntity` and `SelfImprovingEntity` accept a `network` object.  This mismatch causes confusion and failing tests.

**Approach:**
- Modify `Entity.update` to accept a `network` argument and optional `dt`.
- Update `ManualEntity.update` and `SelfImprovingEntity.update` to accept both `network` and optional `dt`.
- Modify `MyceliumNetwork.update` to forward itself and `dt` to each entity.
- Update any documentation accordingly.

**Acceptance criteria:** Tests pass when calling `network.update()` without arguments; each entity receives the network context and optional time delta.

## Quest 2 – Implement serializer
**Description:** Provide utility functions to serialize and deserialize network states and logs.  The current `serializer.py` only contains stubs.

**Approach:**
- Implement functions to serialize a network to a Python dict, JSON file and CSV.
- Implement complementary deserialization functions.
- Integrate with `StateLogger` so that snapshots can be exported and reloaded.

**Acceptance criteria:** A new set of unit tests for serialization passes; exported files can be reloaded to reconstruct equivalent state.

## Quest 3 – Integrate Athena into entities
**Description:** Attach Athena’s perceptual module as a cognitive component of entities in the Manscript‑Being framework.

**Approach:**
- Create an `AthenaAdapter` or similar wrapper to encapsulate `AthenaNeuralNetwork`.
- Extend `ManualEntity`/`SelfImprovingEntity` to initialize an Athena adapter and process sensory inputs within `update`.
- Use classification outputs to set awareness flags and update internal state.

**Acceptance criteria:** Example script demonstrates entities classifying digits with Athena; collective awareness metric reflects classification confidence.

## Quest 4 – Enhance hologram and visualization
**Description:** Improve the `Hologram` projection and add visualization utilities for the mycelium network.

**Approach:**
- Compress high‑dimensional state representations using Athena’s `CompressionPrior`.
- Implement functions to visualize network topology and holographic projections (e.g., using matplotlib or networkx).
- Document usage in the README.

**Acceptance criteria:** Visualization functions produce meaningful plots of network states; projections use compressed representations and are validated in tests.

