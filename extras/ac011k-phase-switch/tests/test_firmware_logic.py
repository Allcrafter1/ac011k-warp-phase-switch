"""Host regression tests compiling the actual firmware method bodies, no hardware IO."""
import pathlib
import subprocess
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[3]


def method(path, signature):
    source = (ROOT / path).read_text()
    start = source.index(signature)
    body = source.index('{', start)
    depth = 1
    end = body + 1
    while depth:
        depth += (source[end] == '{') - (source[end] == '}')
        end += 1
    return source[start:end]


class FirmwareLogic(unittest.TestCase):
    def test_real_start_and_mqtt_methods(self):
        ac = 'software/src/modules/ac011k/ac011k.cpp'
        mqtt = 'software/src/modules/mqtt/mqtt.cpp'
        code = r'''
#include <algorithm>
#include <cassert>
#include <cstdint>
#include <map>
#include <string>
#include <vector>
using std::min;
using String = std::string;
struct Config {
    uint32_t val=0;
    std::map<std::string, Config> fields;
    std::map<int, Config> items;
    Config* get(const char* s) { return &fields[s]; }
    Config* get(int i) { return &items[i]; }
    uint32_t asUint() const { return val; }
    bool asBool() const { return val; }
    void updateUint(uint32_t v) {val=v;}
    void updateBool(bool v) {val=v;}
    void updateString(const char*) {}
};
struct {Config evse_slots,evse_state,evse_hardware_configuration;} evse;
struct {template<class... T> void printfln(const char*, T...) {}} logger;
constexpr int CHARGING_SLOT_COUNT=12, IEC_STATE_A=0, IEC_STATE_C=2;
constexpr int CHARGER_STATE_ERROR=4, CHARGER_STATE_CHARGING=3;
constexpr int PHASE_SWITCH_IDLE=0, PHASE_SWITCH_STOPPING=1, PHASE_SWITCH_OFF_DELAY=2,
PHASE_SWITCH_APPLYING=3, PHASE_SWITCH_CONFIRMING=4, PHASE_SWITCH_RESTARTING=5,
PHASE_SWITCH_RESTART_PAUSE=6, PHASE_SWITCH_ERROR=7;
uint32_t clock_ms=0;
uint32_t millis() {return clock_ms;}
bool deadline_elapsed(uint32_t d) {return uint32_t(clock_ms-d)<UINT32_MAX/2;}
struct AC011K {
    bool initialized=true, firmware_update_running=false;
    int phase_switch_stage=0, sendSequenceNumber=0, starts=0;
    uint8_t StartChargingA6[1]{}, GetStartPowerMode[1]{};
    Config phase_switch_state, phase_switch_config, power_manager_state;
    bool power_target_control_active=false, power_target_dirty=false, resume_after_phase_switch=false,
      physical_phase_verification_pending=false, gd_start_power_get_pending=false,
      gd_close_marker_query_sent=false, gd_close_marker_verified=false,
      phase_switch_cp_safe=false;
    uint8_t gd_start_power_get_reason=0, phase_switch_target=3, restart_attempts=0;
    uint16_t phase_switch_profile_current_ma=0, last_phase_current_deciamp[3]{};
    uint32_t gd_start_power_get_sent_at=0, gd_close_marker_query_started_at=0,
      gd_close_marker_last_query_at=0, last_successful_phase_switch=0,
      phase_switch_stage_since=0, last_phase_current_update=0;
    void process_phase_switch();
    bool phase_switch_supported() {return true;}
    void set_phase_switch_stage(int s) {phase_switch_stage=s; phase_switch_stage_since=millis();}
    void set_phase_switch_error(uint8_t,const char*);
    void update_power_manager_target_state() {}
    void apply_power_manager_current(uint16_t n) {evse.evse_slots.get(8)->get("max_current")->updateUint(n);}
    void send_start_power_mode(uint8_t) {}
    int bs_evse_stop_charging() {return 0;}
    uint16_t charging_current_from_slots();
    int bs_evse_start_charging();
    void sendCommand(uint8_t*,size_t,int,bool=true) {++starts;}
    void sendChargingLimit3(int,int) {}
};
struct Mqtt {
    struct State {uint32_t last_send_ms;};
    std::vector<State> states{{0}};
    Config mqtt_config_in_use;
    int publishes=0;
    bool pushStateUpdate(size_t,const String&,const String&);
    void publish_with_prefix(const String&,const String&) {++publishes;}
};
'''
        code += method(ac, 'uint16_t AC011K::charging_current_from_slots()')
        code += method(ac, 'int AC011K::bs_evse_start_charging()')
        code += method(mqtt, 'bool Mqtt::pushStateUpdate(')
        code += method(ac, 'void AC011K::process_phase_switch()')
        code += method(ac, 'void AC011K::set_phase_switch_error(')
        code += r'''
int main() {
    AC011K box;
    evse.evse_state.get("iec61851_state")->val=1;
    evse.evse_state.get("GD_state")->val=2;
    evse.evse_hardware_configuration.get("GDFirmwareVersion")->val=460;
    for(int i=0;i<CHARGING_SLOT_COUNT;++i) {
        evse.evse_slots.get(i)->get("active")->val=1;
        evse.evse_slots.get(i)->get("max_current")->val=16000;
    }
    evse.evse_slots.get(8)->get("max_current")->val=8000;
    assert(box.bs_evse_start_charging()==0 && box.starts==1);
    assert(evse.evse_state.get("allowed_charging_current")->val==8000);
    // Every active limiting slot vetoes start, even if the aggregate still says 8 A.
    for(int i=0;i<CHARGING_SLOT_COUNT;++i) {
        auto slot=evse.evse_slots.get(i);
        auto saved=slot->get("max_current")->val;
        slot->get("max_current")->val=0;
        assert(box.bs_evse_start_charging()==-1 && box.starts==1);
        slot->get("max_current")->val=saved;
    }
    evse.evse_state.get("iec61851_state")->val=0;
    assert(box.bs_evse_start_charging()==-1 && box.starts==1);
    evse.evse_state.get("iec61851_state")->val=1;
    for(int gd=7;gd<=9;++gd) {
        evse.evse_state.get("GD_state")->val=gd;
        assert(box.bs_evse_start_charging()==-1);
    }
    evse.evse_state.get("GD_state")->val=2;
    box.phase_switch_stage=PHASE_SWITCH_ERROR;
    assert(box.bs_evse_start_charging()==-1 && box.starts==1);
    // 2026-10-06: HA retry reopens release after a CP timeout with a stale
    // 15 A external limit. Error remains latched and no start reaches GD.
    evse.evse_state.get("GD_state")->val=6;
    evse.evse_slots.get(8)->get("max_current")->val=15000;
    evse.evse_slots.get(4)->get("max_current")->val=0;
    assert(box.bs_evse_start_charging()==-1 && box.starts==1);
    evse.evse_slots.get(4)->get("max_current")->val=32000;
    box.process_phase_switch();
    assert(box.phase_switch_stage==PHASE_SWITCH_ERROR);
    assert(box.bs_evse_start_charging()==-1 && box.starts==1);
    box.phase_switch_stage=0;
    box.firmware_update_running=true;
    assert(box.bs_evse_start_charging()==-1 && box.starts==1);
    box.firmware_update_running=false;
    assert(box.bs_evse_start_charging()==0 && box.starts==2);
    // A Stop or unplug during the bounded phase-restart pause cancels retries.
    box.phase_switch_stage=PHASE_SWITCH_RESTART_PAUSE;
    box.phase_switch_stage_since=0;
    clock_ms=2000;
    evse.evse_slots.get(4)->get("max_current")->val=0;
    box.process_phase_switch();
    assert(box.starts==2 && box.phase_switch_stage==PHASE_SWITCH_IDLE);
    evse.evse_slots.get(4)->get("max_current")->val=16000;
    evse.evse_state.get("iec61851_state")->val=0;
    box.phase_switch_stage=PHASE_SWITCH_RESTARTING;
    box.process_phase_switch();
    assert(box.starts==2 && box.phase_switch_stage==PHASE_SWITCH_IDLE);
    // An authorized connected retry still works.
    evse.evse_state.get("iec61851_state")->val=1;
    box.phase_switch_stage=PHASE_SWITCH_RESTART_PAUSE;
    box.phase_switch_stage_since=0;
    box.process_phase_switch();
    assert(box.starts==3 && box.phase_switch_stage==PHASE_SWITCH_RESTARTING);
    // A newer target cancels an obsolete retry before it emits Start.
    box.power_target_control_active=true;
    box.power_target_dirty=true;
    box.phase_switch_stage=PHASE_SWITCH_RESTART_PAUSE;
    box.process_phase_switch();
    assert(box.starts==3 && box.phase_switch_stage==PHASE_SWITCH_IDLE);
    // Stale zero samples must never authorize a relay-mode command.
    box.phase_switch_stage=PHASE_SWITCH_OFF_DELAY;
    box.phase_switch_stage_since=0;
    box.last_phase_current_update=0;
    box.phase_switch_cp_safe=true;
    clock_ms=20000;
    box.process_phase_switch();
    assert(box.phase_switch_stage==PHASE_SWITCH_OFF_DELAY);
    clock_ms=30001;
    box.process_phase_switch();
    assert(box.phase_switch_stage==PHASE_SWITCH_ERROR);
    assert(evse.evse_slots.get(8)->get("max_current")->val==0);
    assert(box.power_manager_state.get("pending")->asBool());
    Mqtt mqtt;
    mqtt.mqtt_config_in_use.get("interval")->val=1;
    clock_ms=999;
    assert(!mqtt.pushStateUpdate(0,"false","evse/auto_start_charging"));
    clock_ms=1000;
    assert(mqtt.pushStateUpdate(0,"false","evse/auto_start_charging"));
    // Real incident: constant state changed only after ~41 days of uptime.
    clock_ms=3550000000U;
    assert(mqtt.pushStateUpdate(0,"false","evse/auto_start_charging"));
    assert(!mqtt.pushStateUpdate(0,"false","evse/auto_start_charging"));
    mqtt.states[0].last_send_ms=UINT32_MAX-500;
    clock_ms=600;
    assert(mqtt.pushStateUpdate(0,"false","evse/auto_start_charging"));
}
'''
        with tempfile.TemporaryDirectory() as d:
            source = pathlib.Path(d) / 'regression.cpp'
            source.write_text(code)
            binary = pathlib.Path(d) / 'regression'
            subprocess.run(['g++', '-std=c++17', '-Wall', '-Wextra', str(source), '-o', str(binary)], check=True)
            subprocess.run([str(binary)], check=True)


if __name__ == '__main__':
    unittest.main()
