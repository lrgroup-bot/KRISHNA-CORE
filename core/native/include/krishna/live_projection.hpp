#pragma once
// KRISHNA native core prototype: C++20, dependency-free, no paid services.
// Read-only projection; authentication and transport belong to the host.
#include <cmath>
#include <cstdint>
#include <map>
#include <stdexcept>
#include <string>
#include <vector>

namespace krishna {
enum class AgentState { idle, working, healing, blocked, offline, unknown };
struct AgentEvent {
  std::string agent_id;
  std::string task_id;
  AgentState state = AgentState::unknown;
  std::uint64_t sequence = 0;
  double timestamp = 0;
  double progress = 0;
  bool verified_completion = false;
};
struct AgentView {
  AgentEvent event;
  bool stale = false;
  AgentState display_state = AgentState::unknown;
  bool verified_completion = false;
};
class LiveProjection {
 public:
  explicit LiveProjection(double max_age_seconds = 30.0)
      : max_age_(max_age_seconds) {
    if (!std::isfinite(max_age_) || max_age_ <= 0)
      throw std::invalid_argument("invalid maximum event age");
  }
  void ingest(const AgentEvent& event, double now) {
    validate(event, now);
    auto found = latest_.find(event.agent_id);
    if (found != latest_.end() && event.sequence <= found->second.sequence)
      throw std::invalid_argument("replayed or out-of-order event");
    latest_[event.agent_id] = event;
  }
  std::vector<AgentView> snapshot(double now) const {
    if (!std::isfinite(now)) throw std::invalid_argument("invalid clock");
    std::vector<AgentView> result;
    for (const auto& [id, event] : latest_) {
      bool stale = now - event.timestamp > max_age_;
      result.push_back({event, stale,
                        stale ? AgentState::unknown : event.state,
                        !stale && event.verified_completion});
    }
    return result;
  }
 private:
  static void validate(const AgentEvent& event, double now) {
    if (event.agent_id.empty() || event.agent_id.size() > 128 ||
        event.task_id.size() > 128 ||
        !std::isfinite(now) || !std::isfinite(event.timestamp) ||
        !std::isfinite(event.progress) ||
        event.timestamp > now + 5 ||
        event.progress < 0 || event.progress > 1)
      throw std::invalid_argument("invalid agent event");
  }
  double max_age_;
  std::map<std::string, AgentEvent> latest_;
};
}  // namespace krishna
