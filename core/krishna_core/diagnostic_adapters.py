from __future__ import annotations

"""Read-only diagnostic evidence adapters for HAWKEYE.

These adapters normalize measurements that are supplied by trusted instruments,
vehicle interfaces or audio/vibration capture. They never transmit on a vehicle
bus, program an ECU, control an instrument, energize a circuit or claim that a
measurement proves a fault by itself.
"""

from pathlib import Path
import hashlib
import json
import math
import time


def _clamp(value, low, high):
    value=float(value)
    return max(low,min(high,value))


def _fingerprint(value):
    raw=json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(",",":"),default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class ElectronicsMeasurementAdapter:
    NAME="electronics-measurement"
    QUANTITIES={
        "voltage":{"V","mV"},
        "current":{"A","mA","uA"},
        "resistance":{"ohm","kohm","Mohm"},
        "continuity":{"bool"},
        "frequency":{"Hz","kHz","MHz"},
        "duty_cycle":{"%"},
        "temperature":{"C","F"},
        "capacitance":{"F","uF","nF","pF"},
    }

    @staticmethod
    def _normalized_volts(quantity,value,unit):
        if quantity!="voltage":return None
        value=float(value)
        return value/1000.0 if unit=="mV" else value

    def ingest(self, measurements, *, source="instrument", reference_id=None,
               captured_at=None, circuit_state="unknown"):
        if not isinstance(measurements,list) or not measurements:
            raise ValueError("at least one electronics measurement is required")
        rows=[];hazard=False
        for item in measurements[:256]:
            if not isinstance(item,dict):continue
            quantity=str(item.get("quantity") or "").strip().lower()
            if quantity not in self.QUANTITIES:
                raise ValueError(f"unsupported electronics quantity: {quantity}")
            unit=str(item.get("unit") or "").strip()
            if unit not in self.QUANTITIES[quantity]:
                raise ValueError(f"unsupported unit {unit!r} for {quantity}")
            point=str(item.get("point") or item.get("test_point") or "").strip()[:160]
            if not point:raise ValueError("measurement point is required")
            if quantity=="continuity":
                value=bool(item.get("value"))
            else:
                value=float(item.get("value"))
                if not math.isfinite(value):raise ValueError("measurement value must be finite")
            volts=self._normalized_volts(quantity,value,unit)
            if volts is not None and abs(volts)>=60.0:hazard=True
            rows.append({
                "point":point,"quantity":quantity,"value":value,"unit":unit,
                "reference":str(item.get("reference") or "")[:160] or None,
                "timestamp":float(item.get("timestamp") or captured_at or time.time()),
            })
        if not rows:raise ValueError("no valid electronics measurements supplied")
        if str(circuit_state or "").lower() in {"mains","high_voltage","energized_hv","traction_battery"}:
            hazard=True
        out={
            "adapter":self.NAME,
            "evidence_state":"MEASURED",
            "source":str(source or "instrument")[:160],
            "reference_id":str(reference_id or "")[:160] or None,
            "circuit_state":str(circuit_state or "unknown")[:80],
            "measurements":rows,
            "measurement_count":len(rows),
            "hazardous_voltage_possible":hazard,
            "safety":{
                "controls_instrument":False,
                "energizes_circuit":False,
                "high_voltage_probe_authorized":False,
                "instruction":(
                    "Treat as potentially hazardous: de-energize/isolate and verify absence of voltage before physical probing."
                    if hazard else
                    "Measurements are evidence only; follow instrument and equipment safety procedures."
                ),
            },
        }
        out["fingerprint"]=_fingerprint(out)
        return out

    def status(self):
        return {
            "adapter":self.NAME,"mode":"read-only supplied measurements",
            "quantities":sorted(self.QUANTITIES),
            "hardware_transport":"adapter_required",
            "controls_hardware":False,"ready":True,
        }


class VehicleReadOnlyAdapter:
    NAME="vehicle-read-only"
    FORBIDDEN={"tx","transmit","write","program","flash","control","actuate","command","send"}

    @staticmethod
    def _bytes(value):
        if isinstance(value,(bytes,bytearray)):return list(value)
        if isinstance(value,str):
            text=value.replace("0x","").replace(","," ").replace("-"," ")
            return [int(x,16) for x in text.split() if x]
        if isinstance(value,(list,tuple)):
            return [int(x) & 0xFF for x in value]
        raise ValueError("vehicle frame data must be bytes, hex text or byte array")

    @staticmethod
    def _obd_pid(mode,pid,data):
        mode=int(mode);pid=int(pid)
        raw=VehicleReadOnlyAdapter._bytes(data)
        decoded=None;name=None;unit=None
        if mode==1 and pid==0x0C and len(raw)>=2:
            name="engine_rpm";decoded=((raw[0]*256)+raw[1])/4.0;unit="rpm"
        elif mode==1 and pid==0x0D and len(raw)>=1:
            name="vehicle_speed";decoded=float(raw[0]);unit="km/h"
        elif mode==1 and pid==0x05 and len(raw)>=1:
            name="coolant_temperature";decoded=float(raw[0])-40.0;unit="C"
        elif mode==1 and pid==0x11 and len(raw)>=1:
            name="throttle_position";decoded=float(raw[0])*100.0/255.0;unit="%"
        return {
            "mode":mode,"pid":pid,"pid_hex":f"{pid:02X}","raw":raw[:64],
            "name":name,"value":decoded,"unit":unit,
            "decoded":decoded is not None,
        }

    @staticmethod
    def _j1939(can_id,data):
        can_id=int(can_id)
        if can_id<0 or can_id>0x1FFFFFFF:raise ValueError("J1939 requires a 29-bit CAN identifier")
        priority=(can_id>>26)&0x7
        dp=(can_id>>24)&0x1
        pf=(can_id>>16)&0xFF
        ps=(can_id>>8)&0xFF
        sa=can_id&0xFF
        pgn=(dp<<16)|(pf<<8)|(ps if pf>=240 else 0)
        return {
            "can_id":can_id,"can_id_hex":f"{can_id:08X}",
            "priority":priority,"pgn":pgn,"pgn_hex":f"{pgn:05X}",
            "source_address":sa,"destination_address":ps if pf<240 else None,
            "data":VehicleReadOnlyAdapter._bytes(data)[:64],
            "spn_decode":"reference_required",
        }

    def ingest(self, protocol, frames, *, source="vehicle-interface", captured_at=None):
        protocol=str(protocol or "").strip().lower()
        if protocol not in {"obd2","can","can-fd","j1939"}:
            raise ValueError("protocol must be obd2, can, can-fd or j1939")
        if not isinstance(frames,list) or not frames:raise ValueError("at least one received frame is required")
        rows=[]
        for item in frames[:1000]:
            if not isinstance(item,dict):continue
            direction=str(item.get("direction") or "rx").strip().lower()
            action=str(item.get("action") or "read").strip().lower()
            if direction in self.FORBIDDEN or action in self.FORBIDDEN:
                raise PermissionError("vehicle diagnostic adapter is read-only; transmit/program/control is prohibited")
            ts=float(item.get("timestamp") or captured_at or time.time())
            if protocol=="obd2":
                row=self._obd_pid(item.get("mode",1),item.get("pid"),item.get("data") or [])
            elif protocol=="j1939":
                row=self._j1939(item.get("can_id"),item.get("data") or [])
            else:
                can_id=int(item.get("can_id"))
                max_id=0x1FFFFFFF if bool(item.get("extended",can_id>0x7FF)) else 0x7FF
                if can_id<0 or can_id>max_id:raise ValueError("CAN identifier outside selected frame format")
                row={
                    "can_id":can_id,"can_id_hex":f"{can_id:X}",
                    "extended":max_id>0x7FF,"data":self._bytes(item.get("data") or [])[:64],
                    "decode":"dbc_or_service_reference_required",
                }
            row.update({"timestamp":ts,"direction":"rx"})
            rows.append(row)
        if not rows:raise ValueError("no valid received vehicle frames supplied")
        out={
            "adapter":self.NAME,"protocol":protocol,"evidence_state":"MEASURED",
            "source":str(source or "vehicle-interface")[:160],"frames":rows,"frame_count":len(rows),
            "safety":{
                "read_only":True,"transmit":False,"ecu_programming":False,
                "actuation":False,"automatic_clear_dtc":False,
            },
            "interpretation_limit":"decoded values are measurements; fault conclusions require service references, context and retest",
        }
        out["fingerprint"]=_fingerprint(out)
        return out

    def status(self):
        return {
            "adapter":self.NAME,"protocols":["obd2","can","can-fd","j1939"],
            "mode":"receive/read evidence only","transport":"hardware_interface_required",
            "transmit":False,"programming":False,"actuation":False,"ready":True,
        }


class AcousticMeasurementAdapter:
    NAME="acoustic-vibration"

    def ingest(self, samples, sample_rate, *, source="microphone", axis=None,
               captured_at=None, max_samples=8192):
        if not isinstance(samples,(list,tuple)) or len(samples)<16:
            raise ValueError("at least 16 acoustic/vibration samples are required")
        rate=float(sample_rate)
        if not 100.0<=rate<=192000.0:raise ValueError("sample_rate outside supported evidence range")
        values=[]
        for value in samples[:max(16,min(int(max_samples),8192))]:
            value=float(value)
            if not math.isfinite(value):raise ValueError("sample values must be finite")
            values.append(value)
        mean=sum(values)/len(values)
        centered=[x-mean for x in values]
        rms=math.sqrt(sum(x*x for x in centered)/len(centered))
        peak=max(abs(x) for x in centered)
        crest=(peak/rms) if rms>1e-12 else 0.0
        crossings=sum(1 for a,b in zip(centered,centered[1:]) if (a<0<=b) or (a>=0>b))
        zcr=crossings/max(1,len(centered)-1)

        # Bounded dependency-free spectrum. Downsample so DFT cost stays small.
        step=max(1,len(centered)//512)
        series=centered[::step][:512]
        effective_rate=rate/step
        n=len(series)
        bins=[]
        for k in range(1,min(n//2,128)):
            re=0.0;im=0.0
            for index,value in enumerate(series):
                angle=2.0*math.pi*k*index/n
                re+=value*math.cos(angle);im-=value*math.sin(angle)
            mag=math.sqrt(re*re+im*im)/n
            bins.append((mag,k*effective_rate/n))
        dominant=[
            {"frequency_hz":round(freq,3),"magnitude":round(mag,8)}
            for mag,freq in sorted(bins,reverse=True)[:5]
        ]
        out={
            "adapter":self.NAME,"evidence_state":"MEASURED",
            "source":str(source or "microphone")[:160],
            "axis":str(axis or "")[:40] or None,
            "captured_at":float(captured_at or time.time()),
            "sample_rate_hz":rate,"sample_count":len(values),
            "features":{
                "mean":round(mean,8),"rms":round(rms,8),"peak":round(peak,8),
                "crest_factor":round(crest,6),"zero_crossing_rate":round(zcr,6),
                "dominant_frequencies":dominant,
            },
            "raw_samples_retained":False,
            "interpretation_limit":"features are measurements; a fault label requires baseline/reference evidence and repeatability",
        }
        out["fingerprint"]=_fingerprint(out)
        return out

    def status(self):
        return {
            "adapter":self.NAME,"mode":"bounded feature extraction from supplied samples",
            "features":["rms","peak","crest_factor","zero_crossing_rate","dominant_frequencies"],
            "raw_samples_retained":False,"capture_transport":"microphone_or_sensor_adapter_required",
            "ready":True,
        }


class DiagnosticAdapterRegistry:
    VERSION="diagnostic-adapters-v1"

    def __init__(self):
        self.electronics=ElectronicsMeasurementAdapter()
        self.vehicle=VehicleReadOnlyAdapter()
        self.acoustic=AcousticMeasurementAdapter()

    def status(self):
        return {
            "version":self.VERSION,
            "electronics":self.electronics.status(),
            "vehicle":self.vehicle.status(),
            "acoustic":self.acoustic.status(),
            "authority":"HAWKEYE DIAGNOSTIC",
            "verification_rule":"measurement -> hypothesis -> next test -> retest; adapters do not verify a fault by themselves",
            "ready":True,
        }
