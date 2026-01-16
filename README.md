# JARVISv4 (Just A Rather Very Intelligent System)

![Status: Active](https://img.shields.io/badge/Status-Active-green.svg)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)

A local-first explicit cognition framework.

## Description
This project implements the **Explicit Cognition Framework (ECF)**, a local-first architecture designed to solve agentic drift. By demoting the LLM to a **stateless reasoning component** and enforcing **deterministic control** via a specialized Controller, JARVISv4 ensures reliability. All state is maintained in **externalized memory artifacts** (Working, Episodic, Semantic), and improvement is driven by **explicit weight learning** rather than context accumulation.

## License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contributions
Contributions are welcome. Please open an issue to discuss proposed changes before submitting a pull request.

## Credits
This work builds upon the foundations laid by [JARVISv2](https://github.com/bentman/JARVISv2) and [JARVISv3](https://github.com/bentman/JARVISv3). It directly leverages high-maturity modules including the **Workflow Engine** (FSM/DAG), **Hardware Detection Service** (NPU/GPU), **Observability** suite, and **Budget/Privacy** enforcement engines.
