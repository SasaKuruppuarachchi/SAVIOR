// SPDX-License-Identifier: GPL-3.0-or-later
// OpenVINS (SAVIOR fork) estimator as an rclcpp component: the body of ov_msckf/src/run_subscribe_msckf.cpp (ROS 2) inside a
// loadable class, so ov_msckf and savior_perception_cpp's savior_node run in ONE component container. With
// use_intra_process_comms the dynamic masks (/savior/mask/left|right, published as unique_ptr by savior_node) reach the
// OpenVINS mask subscription without serialization or copy.
#include <memory>
#include <stdexcept>
#include <string>

#include <rclcpp/rclcpp.hpp>
#include <rclcpp_components/register_node_macro.hpp>

#include "core/VioManager.h"
#include "core/VioManagerOptions.h"
#include "ros/ROS2Visualizer.h"
#include "utils/print.h"
#include "utils/opencv_yaml_parse.h"

namespace savior_ov_component {

class OvMsckfComponent {
 public:
  explicit OvMsckfComponent(const rclcpp::NodeOptions &options) {
    rclcpp::NodeOptions o(options);
    o.allow_undeclared_parameters(true);
    o.automatically_declare_parameters_from_overrides(true);
    node_ = std::make_shared<rclcpp::Node>("run_subscribe_msckf", o);
    std::string config_path = "unset_path_to_config.yaml";
    node_->get_parameter<std::string>("config_path", config_path);
    auto parser = std::make_shared<ov_core::YamlParser>(config_path);
    parser->set_node(node_);
    std::string verbosity = "DEBUG";
    parser->parse_config("verbosity", verbosity);
    ov_core::Printer::setPrintLevel(verbosity);
    ov_msckf::VioManagerOptions params;
    params.print_and_load(parser);
    params.use_multi_threading_subs = !params.deterministic_processing;  // as run_subscribe_msckf (SAVIOR fork)
    sys_ = std::make_shared<ov_msckf::VioManager>(params);
    viz_ = std::make_shared<ov_msckf::ROS2Visualizer>(node_, sys_);
    viz_->setup_subscribers(parser);
    if (!parser->successful()) throw std::runtime_error("ov_msckf: unable to parse all parameters");
    RCLCPP_INFO(node_->get_logger(), "ov_msckf component up (intra-process: %s)",
                options.use_intra_process_comms() ? "on" : "off");
  }
  ~OvMsckfComponent() {
    if (viz_) viz_->visualize_final();
  }
  rclcpp::node_interfaces::NodeBaseInterface::SharedPtr get_node_base_interface() const {
    return node_->get_node_base_interface();
  }

 private:
  rclcpp::Node::SharedPtr node_;
  std::shared_ptr<ov_msckf::VioManager> sys_;
  std::shared_ptr<ov_msckf::ROS2Visualizer> viz_;
};

}  // namespace savior_ov_component

RCLCPP_COMPONENTS_REGISTER_NODE(savior_ov_component::OvMsckfComponent)
