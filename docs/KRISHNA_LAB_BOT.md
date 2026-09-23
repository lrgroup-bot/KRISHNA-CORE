# KRISHNA LAB BOT

LAB BOT is the practical-experiment bridge between BRAHMAGYAN/Rishis and approved laboratory or fabrication hardware.

## Flow

Rishi research question -> LAB BOT experiment request -> design completeness check -> simulation/dry-run -> Sudarshan review -> approved adapter -> measured evidence -> independent replication -> BRAHMA/Gautama/Veda Vyasa review -> Gyan-Bhandar.

## Experiment contract

Each durable experiment can record:

- requesting Rishi and provenance/source references;
- hypothesis and objective;
- domain and execution mode;
- independent/dependent variables;
- controls and planned measurements;
- success criteria and limitations;
- requested artifact/output;
- minimum independent replication;
- adapter, review state, execution state and evidence.

A missing control, measurement or success criterion causes simulation verification to fail closed as DESIGN_INCOMPLETE.

## Execution modes

- **simulation**: built-in, no physical claim;
- **measurement**: approved bench/sensor adapters;
- **fabrication**: approved fabrication adapters;
- **wet_lab**: approved laboratory automation adapters.

Rishis can create, inspect and simulate experiments through the Shared Action Bus. They do not receive raw shell or unrestricted hardware-control access.

Physical execution uses the separate `lab.experiment.execute` action, which requires explicit approval. Biological/biomedical/medical/pharmacological/chemical/wet-lab work additionally requires protocol review, facility approval and a confirmed human operator.

## Adapter model

The built-in simulation adapter validates the experiment structure. Physical adapters are explicit capability-scoped plugins. Initial target families include:

- PyLabRobot-compatible laboratory automation;
- Opentrons Python Protocol API;
- bench electrical/measurement instruments;
- microscopy and imaging;
- acoustic signal/measurement rigs;
- approved fabrication hardware.

An adapter is not treated as physically available merely because software support exists. It remains hardware-unverified until connected and accepted on the real device.

## Scientific evidence

An adapter completing a run means only that the run completed. It does not automatically prove the hypothesis. LAB BOT retains successes and failures, and the result remains pending verification until independent replication/review is complete. Only then may BRAHMA propose the finding for trusted Gyan-Bhandar promotion.


## Quantum Lab and Nano Lab

LAB BOT includes a software-first Quantum/Nano research layer.

### Quantum Lab

Quantum Lab can:

- create evidence-bounded quantum research plans;
- require matched classical baselines;
- run a bounded local state-vector simulator for small circuits;
- model basic gates and entanglement workflows;
- detect optional Qiskit and PennyLane installations;
- plan Hamiltonian, variational, quantum-chemistry, QML and quantum-sensing studies.

A simulator result is always labeled as classical simulation. Software presence never means a real QPU is connected, and no quantum-advantage claim is accepted without a valid matched benchmark.

### Nano Lab

Nano Lab can:

- calculate bounded nanoscale geometry descriptors such as surface-to-volume ratio;
- plan structure, surface, defect/interface, electronic, optical and mechanical analyses;
- detect optional pymatgen and ASE installations;
- prepare future Materials Project/provider workflows;
- connect nanotechnology research to LAB BOT evidence and replication.

Geometric descriptors are not material-property predictions. Atomistic or electronic-structure results must preserve the calculator/model, assumptions, convergence information and reference comparison.

### Quantum + Nano intersection

The joint research bridge prioritizes:

- quantum materials;
- quantum dots;
- nanophotonics;
- spin-defect sensing;
- nanoscale quantum sensors;
- mesoscopic/superconducting devices;
- molecular and materials quantum simulation.

The workflow is software-first: define a measurable target, establish a classical/materials baseline, simulate, quantify uncertainty, compare with trusted evidence, then design any physical test.

Physical nanofabrication, quantum-hardware operation, quantum-materials fabrication and nanomaterials laboratory execution are not enabled merely by software support. They require registered physical adapters, protocol review, owner/Sudarshan approval, facility approval and a confirmed human operator before LAB BOT may execute them.
