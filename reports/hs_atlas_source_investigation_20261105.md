# Atlas: source-first engineering capability discovery

**Objective:** Identify reusable open-source engineering capabilities that Hardware Splicer could integrate rather than reimplement.

This is objective-profile-driven GitHub search, existing Atlas lexical triage, and SHA-pinned Git source-code presence verification. This is NOT free-form autonomous planning or proven integrations.

Provider candidates: 43. Bounded original GitHub code probes: 13. Capability areas with at least one implementation literal: 5/5.

| Capability | First review candidate (not a winner) | GitHub first result | Code indicator observed |
|---|---|---|---|
| Robot Urdf | HoangGiang93/urdf_importer | Unity-Technologies/URDF-Importer | Yes (not run) |
| Parametric Cad | CadQuery/cadquery | CadQuery/cadquery | Yes (not run) |
| Pcb Validation | archimedes-market/mcp-kicad-pcb-inspector | salitronic/eda-agent | Yes (not run) |
| Printer Interface | DMontgomery40/mcp-3D-printer-server | DMontgomery40/mcp-3D-printer-server | Yes (not run) |
| Bom Tools | AlexanderNickolsky/KiCad-Better-BOM | kylemanna/kicad-utils | Yes (not run) |

## Source-pinned engineering review queue

### Robot Urdf

**Question:** Find reusable URDF import and robot simulation components.

**Provider search:** robot URDF importer

**Candidate metadata matches:** 9; query outcome: ok

**HoangGiang93/urdf_importer** — CODE_LITERAL_OBSERVED_NOT_TESTED

Pinned commit: f73d1585df2b15816c121eb195c2379f4e8c30de; GitHub license metadata: MIT (legal review required).

- [urdf_importer_addon/urdf_importer/robot_builder.py](https://github.com/HoangGiang93/urdf_importer/blob/f73d1585df2b15816c121eb195c2379f4e8c30de/urdf_importer_addon/urdf_importer/robot_builder.py) — exact Git blob 4c1e9bdf920b501b9310931aa9192eb3ab247d4c; literal code indicator: urdf; external code not executed.
- [urdf_importer_addon/__init__.py](https://github.com/HoangGiang93/urdf_importer/blob/f73d1585df2b15816c121eb195c2379f4e8c30de/urdf_importer_addon/__init__.py) — exact Git blob 28aa858cef88e7f36e94323c01f4245f6b380408; literal code indicator: urdf; external code not executed.

**Unity-Technologies/URDF-Importer** — CODE_LITERAL_OBSERVED_NOT_TESTED

Pinned commit: 90f353e4352aae4df52fa2c05e49b804631d2a63; GitHub license metadata: Apache-2.0 (legal review required).

- [com.unity.robotics.urdf-importer/Editor/CustomEditors/HingeJointLimitsManagerEditor.cs](https://github.com/Unity-Technologies/URDF-Importer/blob/90f353e4352aae4df52fa2c05e49b804631d2a63/com.unity.robotics.urdf-importer/Editor/CustomEditors/HingeJointLimitsManagerEditor.cs) — exact Git blob 885d2ec5038c17302e25eb6d55e2111b03989330; literal code indicator: urdf; external code not executed.
- [com.unity.robotics.urdf-importer/Editor/CustomEditors/InspectorReadOnlyAttributeDrawer.cs](https://github.com/Unity-Technologies/URDF-Importer/blob/90f353e4352aae4df52fa2c05e49b804631d2a63/com.unity.robotics.urdf-importer/Editor/CustomEditors/InspectorReadOnlyAttributeDrawer.cs) — exact Git blob b436580f7520a43e17e5a36936931550ad7153c4; literal code indicator: not found; external code not executed.

**kralf/blender-urdf** — CODE_LITERAL_OBSERVED_NOT_TESTED

Pinned commit: 9eeba46f7bec9c68189e14028b275f28e2f40fb7; GitHub license metadata: LGPL-3.0 (legal review required).

- [src/io_scene_urdf/urdf/robot.py](https://github.com/kralf/blender-urdf/blob/9eeba46f7bec9c68189e14028b275f28e2f40fb7/src/io_scene_urdf/urdf/robot.py) — exact Git blob 7a4b1dc8afa72857f1b226cc3c8f71d49e9ca078; literal code indicator: urdf; external code not executed.
- [src/io_scene_urdf/__init__.py](https://github.com/kralf/blender-urdf/blob/9eeba46f7bec9c68189e14028b275f28e2f40fb7/src/io_scene_urdf/__init__.py) — exact Git blob 27f7cdeda19bc82e3ca06b6d98b51454abe9171c; literal code indicator: urdf; external code not executed.

**Existing target repository:** Spectating101/hardware-splicer (default branch only; does not inspect open PRs).

**Possible existing capability indicator:** POSSIBLE_ALREADY_IMPLEMENTED_CHECK_FUNCTIONAL_EQUIVALENCE.

- [Existing source file apps/3d-splicer/src/decomposition/simulation/physics_engine.py](https://github.com/Spectating101/hardware-splicer/blob/38dbad2b759a9313b81a5b10bfde7f20d64f308c/apps/3d-splicer/src/decomposition/simulation/physics_engine.py) — pinned SHA 2bc3d30d80740de8c1d35458d246e46255389236; literal token joint. This is NOT proof of functional duplication.
- [Existing source file apps/3d-splicer/src/decomposition/simulation/stress_test.py](https://github.com/Spectating101/hardware-splicer/blob/38dbad2b759a9313b81a5b10bfde7f20d64f308c/apps/3d-splicer/src/decomposition/simulation/stress_test.py) — pinned SHA d3e75017984a173a4770ea88156f8d030fcfe252; literal token not found. This is NOT proof of functional duplication.

**Next falsifying engineering test:** Run an independent URDF fixture and compare parsed joint origins, axes, and limits.

**Equal-evidence alternatives:** HoangGiang93/urdf_importer, Unity-Technologies/URDF-Importer, kralf/blender-urdf. A tied evidence score never establishes a technical winner.

**Disposition:** REVIEW_EXISTING_TARGET_CODE_BEFORE_ANY_LIBRARY_ADOPTION

### Parametric Cad

**Question:** Find scriptable, parametric CAD components for product geometry.

**Provider search:** CAD parametric modeling python

**Candidate metadata matches:** 8; query outcome: ok

**CadQuery/cadquery** — CODE_LITERAL_OBSERVED_NOT_TESTED

Pinned commit: 8178185a24a035c9af7f4679033be14267f6a6ef; GitHub license metadata: NOASSERTION (legal review required).

- [cadquery/cq_directive.py](https://github.com/CadQuery/cadquery/blob/8178185a24a035c9af7f4679033be14267f6a6ef/cadquery/cq_directive.py) — exact Git blob 3749c379f225b9eb1e35525a33d0db3cce9d46dd; literal code indicator: shape; external code not executed.
- [cadquery/cqgi.py](https://github.com/CadQuery/cadquery/blob/8178185a24a035c9af7f4679033be14267f6a6ef/cadquery/cqgi.py) — exact Git blob 2b7c301a5158982fb2ce2526ea3169e76c5f85c6; literal code indicator: cadquery; external code not executed.

**JonFermin/cadsmith** — METADATA_ONLY_ABSTAIN

Pinned commit: 00c334dd4202116091e2cca75296333757947366; GitHub license metadata: MIT (legal review required).

- No implementation file witnessed; provider description alone is insufficient.

**Existing target repository:** Spectating101/hardware-splicer (default branch only; does not inspect open PRs).

**Possible existing capability indicator:** POSSIBLE_ALREADY_IMPLEMENTED_CHECK_FUNCTIONAL_EQUIVALENCE.

- [Existing source file apps/3d-splicer/src/core/cadquery_generator.py](https://github.com/Spectating101/hardware-splicer/blob/38dbad2b759a9313b81a5b10bfde7f20d64f308c/apps/3d-splicer/src/core/cadquery_generator.py) — pinned SHA 9cca02ab96fbb986fc11cfbca81ff35b8a27388d; literal token cadquery. This is NOT proof of functional duplication.
- [Existing source file apps/circuit-ai/circuit-ai-frontend/app/api/proxy/validate-kicad/route.ts](https://github.com/Spectating101/hardware-splicer/blob/38dbad2b759a9313b81a5b10bfde7f20d64f308c/apps/circuit-ai/circuit-ai-frontend/app/api/proxy/validate-kicad/route.ts) — pinned SHA 88c469187f9c40d9314dec817b51bd454da7d68e; literal token not found. This is NOT proof of functional duplication.

**Next falsifying engineering test:** Build an editable parameterized sample and export STEP and mesh with dimensional assertions.

**Equal-evidence alternatives:** CadQuery/cadquery. A tied evidence score never establishes a technical winner.

**Disposition:** REVIEW_EXISTING_TARGET_CODE_BEFORE_ANY_LIBRARY_ADOPTION

### Pcb Validation

**Question:** Find reusable KiCad PCB inspection and design-rule automation.

**Provider search:** KiCad PCB DRC automation

**Candidate metadata matches:** 9; query outcome: ok

**archimedes-market/mcp-kicad-pcb-inspector** — CODE_LITERAL_OBSERVED_NOT_TESTED

Pinned commit: a9879dddbafd358ccdb858af7ca2a95a827752e2; GitHub license metadata: MIT (legal review required).

- [src/mcp_kicad_pcb_inspector/__init__.py](https://github.com/archimedes-market/mcp-kicad-pcb-inspector/blob/a9879dddbafd358ccdb858af7ca2a95a827752e2/src/mcp_kicad_pcb_inspector/__init__.py) — exact Git blob dd24584d1fca838ac30bf207eee60935eb1a05a0; literal code indicator: kicad; external code not executed.
- [src/mcp_kicad_pcb_inspector/cli.py](https://github.com/archimedes-market/mcp-kicad-pcb-inspector/blob/a9879dddbafd358ccdb858af7ca2a95a827752e2/src/mcp_kicad_pcb_inspector/cli.py) — exact Git blob 2237462855a9334e5c954ad5d7359b32a819bf6f; literal code indicator: kicad; external code not executed.

**salitronic/eda-agent** — CODE_LITERAL_OBSERVED_NOT_TESTED

Pinned commit: b1a2f60806fbf690d1c2e27686c3594862186a59; GitHub license metadata: Apache-2.0 (legal review required).

- [src/eda_agent/core/kicad_drc.py](https://github.com/salitronic/eda-agent/blob/b1a2f60806fbf690d1c2e27686c3594862186a59/src/eda_agent/core/kicad_drc.py) — exact Git blob 4e6e1988fcc4bca6338e8c84d7cbcfa2a3517f2b; literal code indicator: kicad; external code not executed.
- [src/eda_agent/core/kicad_pcb.py](https://github.com/salitronic/eda-agent/blob/b1a2f60806fbf690d1c2e27686c3594862186a59/src/eda_agent/core/kicad_pcb.py) — exact Git blob 5d2f57e4776e136b8eaf6e78bb232320586dcad4; literal code indicator: kicad; external code not executed.

**kehindejanetolaniyi23/home-automation-kicad-work-in-progress** — METADATA_ONLY_ABSTAIN

Pinned commit: 2b75f4455bb1c829ec8686049fd8df2762133cdb; GitHub license metadata: unknown (legal review required).

- No implementation file witnessed; provider description alone is insufficient.

**Existing target repository:** Spectating101/hardware-splicer (default branch only; does not inspect open PRs).

**Possible existing capability indicator:** POSSIBLE_ALREADY_IMPLEMENTED_CHECK_FUNCTIONAL_EQUIVALENCE.

- [Existing source file apps/circuit-ai/circuit-ai-frontend/lib/pcb/drc.ts](https://github.com/Spectating101/hardware-splicer/blob/38dbad2b759a9313b81a5b10bfde7f20d64f308c/apps/circuit-ai/circuit-ai-frontend/lib/pcb/drc.ts) — pinned SHA 318c6821ea4179936e1a21628e05e1722c5e4d90; literal token drc. This is NOT proof of functional duplication.
- [Existing source file apps/circuit-ai/circuit-ai-frontend/app/api/proxy/validate-kicad/route.ts](https://github.com/Spectating101/hardware-splicer/blob/38dbad2b759a9313b81a5b10bfde7f20d64f308c/apps/circuit-ai/circuit-ai-frontend/app/api/proxy/validate-kicad/route.ts) — pinned SHA 88c469187f9c40d9314dec817b51bd454da7d68e; literal token kicad. This is NOT proof of functional duplication.

**Next falsifying engineering test:** Run on known KiCad boards with planted shorts or clearance violations; compare against KiCad's DRC.

**Equal-evidence alternatives:** archimedes-market/mcp-kicad-pcb-inspector, salitronic/eda-agent. A tied evidence score never establishes a technical winner.

**Disposition:** REVIEW_EXISTING_TARGET_CODE_BEFORE_ANY_LIBRARY_ADOPTION

### Printer Interface

**Question:** Find device-independent 3D printer command/monitor interfaces with safety gates.

**Provider search:** 3D printer MCP OctoPrint

**Candidate metadata matches:** 6; query outcome: ok

**DMontgomery40/mcp-3D-printer-server** — CODE_LITERAL_OBSERVED_NOT_TESTED

Pinned commit: 29a06af87f1d52fb2c72a3013ed0feeed7cb602f; GitHub license metadata: GPL-2.0 (legal review required).

- [src/printers/klipper.ts](https://github.com/DMontgomery40/mcp-3D-printer-server/blob/29a06af87f1d52fb2c72a3013ed0feeed7cb602f/src/printers/klipper.ts) — exact Git blob 0420b9a5388f223d33223f9d835b144bedc9102c; literal code indicator: klipper; external code not executed.
- [src/printers/octoprint.ts](https://github.com/DMontgomery40/mcp-3D-printer-server/blob/29a06af87f1d52fb2c72a3013ed0feeed7cb602f/src/printers/octoprint.ts) — exact Git blob 82add72087f76d0ad039605544c9f14eb5f1b89c; literal code indicator: octoprint; external code not executed.

**Villocity-Labs/mcp-printer** — CODE_LITERAL_OBSERVED_NOT_TESTED

Pinned commit: b9aa78ade7ebd47a2553565ab1da20389addf843; GitHub license metadata: MIT (legal review required).

- [mcp_printer/__init__.py](https://github.com/Villocity-Labs/mcp-printer/blob/b9aa78ade7ebd47a2553565ab1da20389addf843/mcp_printer/__init__.py) — exact Git blob c2c9121a0b2f8ed3371d9b7c35590d2d2da95e26; literal code indicator: printer; external code not executed.
- [mcp_printer/__main__.py](https://github.com/Villocity-Labs/mcp-printer/blob/b9aa78ade7ebd47a2553565ab1da20389addf843/mcp_printer/__main__.py) — exact Git blob 3c63a7b4bee6a28c84fae85c79c93ea39b697b48; literal code indicator: printer; external code not executed.

**Existing target repository:** Spectating101/hardware-splicer (default branch only; does not inspect open PRs).

**Possible existing capability indicator:** POSSIBLE_ALREADY_IMPLEMENTED_CHECK_FUNCTIONAL_EQUIVALENCE.

- [Existing source file apps/3d-splicer/src/template_generation/printer/printer.py](https://github.com/Spectating101/hardware-splicer/blob/38dbad2b759a9313b81a5b10bfde7f20d64f308c/apps/3d-splicer/src/template_generation/printer/printer.py) — pinned SHA c8706a12b14d39c0d1df5aea1820fcf71915bee6; literal token printer. This is NOT proof of functional duplication.
- [Existing source file apps/circuit-ai/circuit-ai-mcp/src/index.ts](https://github.com/Spectating101/hardware-splicer/blob/38dbad2b759a9313b81a5b10bfde7f20d64f308c/apps/circuit-ai/circuit-ai-mcp/src/index.ts) — pinned SHA f7ea576e513e3b39b9241476e81eb772ff34c48d; literal token mcp. This is NOT proof of functional duplication.

**Next falsifying engineering test:** Exercise a simulator/mocked printer only; require operator approval before any physical action.

**Equal-evidence alternatives:** DMontgomery40/mcp-3D-printer-server, Villocity-Labs/mcp-printer. A tied evidence score never establishes a technical winner.

**Disposition:** REVIEW_EXISTING_TARGET_CODE_BEFORE_ANY_LIBRARY_ADOPTION

### Bom Tools

**Question:** Find KiCad bill-of-materials generation and electronics sourcing adapters.

**Provider search:** KiCad BOM generator

**Candidate metadata matches:** 8; query outcome: ok

**AlexanderNickolsky/KiCad-Better-BOM** — CODE_LITERAL_OBSERVED_NOT_TESTED

Pinned commit: 37a169217842676403f3ee810c66bffd0885b15e; GitHub license metadata: MIT (legal review required).

- [kicad_bom.py](https://github.com/AlexanderNickolsky/KiCad-Better-BOM/blob/37a169217842676403f3ee810c66bffd0885b15e/kicad_bom.py) — exact Git blob bed20f928619b9e121728559efd9d3f18ad84052; literal code indicator: kicad; external code not executed.

**kylemanna/kicad-utils** — CODE_LITERAL_OBSERVED_NOT_TESTED

Pinned commit: 0d8b015509d785f4c44ee4922590fe89e79248d6; GitHub license metadata: MIT (legal review required).

- [kicad_unified_bom_xyrs.py](https://github.com/kylemanna/kicad-utils/blob/0d8b015509d785f4c44ee4922590fe89e79248d6/kicad_unified_bom_xyrs.py) — exact Git blob 2f66421ddf44d4c12a67393a5c486f31deb66583; literal code indicator: bom; external code not executed.
- [kicad_netlist_reader.py](https://github.com/kylemanna/kicad-utils/blob/0d8b015509d785f4c44ee4922590fe89e79248d6/kicad_netlist_reader.py) — exact Git blob 407f5725041cf031c8f1d902d5b28b87f22e4b1c; literal code indicator: bom; external code not executed.

**mondalaci/kicad-bom-generator** — CODE_LITERAL_OBSERVED_NOT_TESTED

Pinned commit: 7fdf5b90564d0d81409475620b5708b1241cfb10; GitHub license metadata: GPL-3.0 (legal review required).

- [bin/kicad-bom-generator.js](https://github.com/mondalaci/kicad-bom-generator/blob/7fdf5b90564d0d81409475620b5708b1241cfb10/bin/kicad-bom-generator.js) — exact Git blob e89a1a5ba0bbb0e057217b900bf0c2f4d8f73238; literal code indicator: kicad; external code not executed.

**Existing target repository:** Spectating101/hardware-splicer (default branch only; does not inspect open PRs).

**Possible existing capability indicator:** POSSIBLE_ALREADY_IMPLEMENTED_CHECK_FUNCTIONAL_EQUIVALENCE.

- [Existing source file apps/circuit-ai/circuit-ai-frontend/components/cad/pcb-viewport.tsx](https://github.com/Spectating101/hardware-splicer/blob/38dbad2b759a9313b81a5b10bfde7f20d64f308c/apps/circuit-ai/circuit-ai-frontend/components/cad/pcb-viewport.tsx) — pinned SHA 37e4ab6e979c039ebc640555c4162fffb1bf8825; literal token bom. This is NOT proof of functional duplication.
- [Existing source file apps/3d-splicer/src/decomposition/core/component.py](https://github.com/Spectating101/hardware-splicer/blob/38dbad2b759a9313b81a5b10bfde7f20d64f308c/apps/3d-splicer/src/decomposition/core/component.py) — pinned SHA 00df88af75951261cefe1dc7d39410b0a4424298; literal token component. This is NOT proof of functional duplication.

**Next falsifying engineering test:** Generate BOM for a known KiCad fixture and check item counts, fields and duplicates.

**Equal-evidence alternatives:** AlexanderNickolsky/KiCad-Better-BOM, kylemanna/kicad-utils, mondalaci/kicad-bom-generator. A tied evidence score never establishes a technical winner.

**Disposition:** REVIEW_EXISTING_TARGET_CODE_BEFORE_ANY_LIBRARY_ADOPTION

## What the baseline comparison means

Plain GitHub search baseline = first relevance result for each identical query. The Atlas-first result is ordered by available original code-file evidence after a small, bounded lexical source screening. Both first-result and Atlas candidates receive the same SHA/blob check. This is not an unbiased performance study, and missing source files do not imply no capability.

Plain first-result code indicators: 5/5; Atlas-ranked code indicators: 5/5.

**No integrations were executed. Licensing, API semantics, safety, maintainability, cost and engineering usefulness require a separate operator-controlled test.**

Existing Hardware Splicer code indicators are limited to its default branch, not draft/open PRs. A shared token is not functional equivalence and should trigger a comparison test, not automatically block adoption.

All source observations remain review-only; no automatic merging, hardware actions, or trusted registration.
