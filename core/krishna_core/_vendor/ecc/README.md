# ECC reference subset for KRISHNA

Source: https://github.com/affaan-m/ECC at commit
`b38be6a7f6350964d59328b52f0624e1d1d552d1` (2026-10-30).

This directory contains only six selected upstream skill documents and the
upstream MIT `LICENSE`. They are reference material, not installed skills,
runtime hooks, agents, commands, model providers, or execution authority.
KRISHNA uses a small reviewed interpretation in `core/krishna_core/ecc_workflows.py`.
Changing a copied file makes that advisory unavailable until its hash and
reviewed interpretation are updated together.

| Upstream file | SHA-256 of copied bytes |
| --- | --- |
| `LICENSE` | `326146379f01bb137c0a5d3c54770c1aa31076705c8b88a7f6b26a460f6221b2` |
| `skills/agentic-engineering/SKILL.md` | `c626eb66387447af2878a686977e3e95476fe441a46dcab82f3163d7f8e2b66d` |
| `skills/iterative-retrieval/SKILL.md` | `b453b16d3e36174b8487c05ab807d0321a66c2d058812b2ae129d82824183725` |
| `skills/ai-regression-testing/SKILL.md` | `83f2f5c4083af5762dd658f742d4a390eb3a6f969d835f69e8f47efba296c127` |
| `skills/contract-first/SKILL.md` | `3eaacf16a9bbd92888659e9c1e15b0fa4eb96a41c257dd9e08f2e63b824f0cea` |
| `skills/frontend-design-direction/SKILL.md` | `71a40f7bc4a28da01b54527fe5590f6055c93adc630e6ceee8c892b35c980893` |
| `skills/agent-security-hardening/SKILL.md` | `0e0895ada90aa8fa085e4257961ebe15f2dff43b843785b1533d4c731186ad81` |

ECC's prose may mention paid models, cloud services, shell commands, or a
different agent harness. Those instructions do not override KRISHNA's local-only,
zero-spend, isolation, KABACH, owner approval, and independent QC rules. No
ECC installer or package is executed by this integration.
