# GARUDA Engine — architecture and diagnostic coverage (design; NOT implemented)

GARUDA is a deterministic, auditable **engine**, not a conversational agent. HAWKEYE is its mobile field interface. KRISHNA coordinates policy and approvals. This design supplements docs/HAWKEYE_ELECTRONICS_DIAGNOSTIC_LAB.md.

## Engines / subsystems
1. **Discovery bus:** OS device notifications for USB, SATA, PCIe, memory configuration changes and enrolled LAN/Wi-Fi hosts; Bluetooth pairing/service discovery; deduplicate by stable identity. A discovered network host is NOT remotely manageable without authenticated enrollment.
2. **Hardware fingerprint and inventory:** OS APIs + osquery/GLPI-style collectors; collect CPU, memory, GPU, bus IDs, storage controller, firmware, temperature sensor availability; record confidence and provenance.
3. **Device capability registry:** Driver/plugin contracts per device class: supported interfaces, required instruments, non-invasive checks, stress tests, destructive operations, prerequisites and abort conditions. Never claim universal coverage.
4. **Diagnostic orchestrator:** User selects target; displays FULL PRO plan; target admin approval; checks power/temperature/health/data criticality; runs supported tests with per-test timeouts, isolation, thermal cutoffs, watchdog and cancellation. Unsupported checks become NOT_TESTED. Destructive operations, firmware updates, power cycling, reboots and write tests require separate specific approval.
5. **Evidence and report:** Raw command outputs, tool versions, calibration information, timestamps, photos, operator measurements, checksums; PASS/WARN/FAIL/NOT_TESTED; suitability and repair/reuse recommendations.
6. **Workload scheduler:** Enrolled-node heartbeat, utilization and reservations; dependency DAG and priority; route compatible jobs by observed performance, remaining RAM/VRAM, disk I/O and thermal headroom. Separate scheduling from diagnostic testing; no stress tests on production workers during active jobs.
7. **Model compatibility evaluator:** Vendor-confirmed model specs, runtime/quantization compatibility and measured benchmarks. No guarantee based on aggregate cluster RAM.
8. **HAWKEYE bridge:** Mobile camera/voice intake, instrument readouts, progress, owner approval and LR Resources inventory handoff.

## Reference projects for evaluation, not blind imports
- smartmontools/smartmontools: SMART and storage health; USB bridges may block pass-through.
- ashaduri/gsmartcontrol: SMART UI and supported self-tests.
- osquery/osquery: cross-platform local system inventory.
- glpi-project/glpi-agent: network discovery/inventory via ICMP/ARP/SNMP.
- netboxlabs/orb-agent: network discovery and SNMP/gNMI.
- prometheus/node_exporter and prometheus-community/windows_exporter: performance telemetry.
- LibreHardwareMonitor/LibreHardwareMonitor: Windows sensor monitoring.
Evaluate license, OS compatibility, maintenance, privilege model and integration testing before dependency selection.

## Mandatory storage recovery guard
On a newly attached HDD/SSD: first enumerate identity and controller capability. If clicking, repeated resets/disconnects, unreadable sectors, suspected head failure, critical footage/data or unknown provenance: enter RECOVERY_PROTECT. No SMART self-test, surface scan, benchmark, repeated spin-up, filesystem repair, initialization, format or write operation. Alert operator; recommend controlled professional imaging/recovery. USB-SATA adapters can conceal SMART; mark unsupported rather than guessing.

## Tests by class
- Healthy HDD/SSD: identity, SMART when supported, thermal/error history, read-only tests after preflight; no write benchmark on user data.
- CPU/RAM/GPU: model/firmware/sensors, benchmark, controlled stress and thermal throttling, memory stability; RAM module testing may require compatible motherboard and reboot.
- Switch/router: inventory, SNMP/management API where authorized, per-port negotiated link, packet loss/throughput with endpoints, PoE with calibrated tester.
- TV/monitor: EDID, supported modes, test patterns, manual pixel inspection; calibrated colorimeter for brightness/color.
- UPS/power electronics: telemetry, safe instrument-assisted measurements; no automatic mains probing or unsafe load switching.
- Other electronics: inspect and report device-specific capabilities; NOT_TESTED where inaccessible.

## Required UI
KRISHNA main menu: GARUDA Engine -> Discovered Devices / Selected Device / PRO Diagnostics / Live Health / Workload Distributor / Model Compatibility / Reports / HAWKEYE Electronics Lab.

## Acceptance gates
- Authorized device selection only; no privilege bypass.
- No stress testing of unknown/failing/critical-data disks.
- Tested, failed and not-tested distinctions preserved.
- Reproducible logs, abort handling, rollback/recovery of interrupted jobs.
- Benchmarked scheduler avoids bottlenecks, uses reservations and respects active workloads.
- Device-class adapters tested on real equipment; no universal-support claim.
