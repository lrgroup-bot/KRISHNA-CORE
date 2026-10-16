#include "krishna/live_projection.hpp"
#include <cassert>
#include <stdexcept>
int main() {
  krishna::LiveProjection projection(30);
  krishna::AgentEvent event;
  event.agent_id = "sudarshan";
  event.task_id = "project-1";
  event.state = krishna::AgentState::working;
  event.sequence = 1;
  event.timestamp = 100;
  event.progress = 0.5;
  projection.ingest(event, 101);
  assert(projection.snapshot(101).at(0).display_state == krishna::AgentState::working);
  bool rejected = false;
  try { projection.ingest(event, 102); }
  catch (const std::invalid_argument&) { rejected = true; }
  assert(rejected);
  assert(projection.snapshot(131).at(0).stale);
  assert(!projection.snapshot(131).at(0).verified_completion);
}
