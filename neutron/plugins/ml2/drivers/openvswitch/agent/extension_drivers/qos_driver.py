# Copyright (c) 2015 OpenStack Foundation
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import collections

from neutron_lib import constants
from neutron_lib.services.qos import constants as qos_consts
from oslo_config import cfg
from oslo_log import log as logging

from neutron.agent.l2.extensions import qos_linux as qos
from neutron.services.qos.drivers.openvswitch import driver


LOG = logging.getLogger(__name__)


class QosOVSAgentDriver(qos.QosLinuxAgentDriver):

    SUPPORTED_RULES = driver.SUPPORTED_RULES

    def __init__(self):
        super(QosOVSAgentDriver, self).__init__()
        self.br_int_name = cfg.CONF.OVS.integration_bridge
        self.br_int = None
        self.agent_api = None
        self.ports = collections.defaultdict(dict)

    def consume_api(self, agent_api):
        self.agent_api = agent_api

    def _qos_bandwidth_initialize(self):
        """Clear QoS setting at agent restart.

        This is for clearing stale settings (such as ports and QoS tables
        deleted while the agent is down). The current implementation
        can not find stale settings. The solution is to clear everything and
        rebuild. There is no performance impact however the QoS feature will
        be down until the QoS rules are rebuilt.
        """
        self.br_int.clear_bandwidth_qos()
        self.br_int.set_queue_for_ingress_bandwidth_limit()

    def initialize(self):
        self.br_int = self.agent_api.request_int_br()
        self.cookie = self.br_int.default_cookie
        self._qos_bandwidth_initialize()

    def create_bandwidth_limit(self, port, rule):
        self.update_bandwidth_limit(port, rule)

    def update_bandwidth_limit(self, port, rule):
        vif_port = port.get('vif_port')
        if not vif_port:
            port_id = port.get('port_id')
            LOG.debug("update_bandwidth_limit was received for port %s but "
                      "vif_port was not found. It seems that port is already "
                      "deleted", port_id)
            return
        self.ports[port['port_id']][(qos_consts.RULE_TYPE_BANDWIDTH_LIMIT,
                                     rule.direction)] = port
        if rule.direction == constants.INGRESS_DIRECTION:
            self._update_ingress_bandwidth_limit(vif_port, rule)
        else:
            self._update_egress_bandwidth_limit(vif_port, rule)

    def delete_bandwidth_limit(self, port):
        port_id = port.get('port_id')
        vif_port = port.get('vif_port')
        port = self.ports[port_id].pop((qos_consts.RULE_TYPE_BANDWIDTH_LIMIT,
                                        constants.EGRESS_DIRECTION),
                                       None)

        if not port and not vif_port:
            LOG.debug("delete_bandwidth_limit was received "
                      "for port %s but port was not found. "
                      "It seems that bandwidth_limit is already deleted",
                      port_id)
            return
        vif_port = vif_port or port.get('vif_port')
        self.br_int.delete_egress_bw_limit_for_port(vif_port.port_name)

    def delete_bandwidth_limit_ingress(self, port):
        port_id = port.get('port_id')
        vif_port = port.get('vif_port')
        port = self.ports[port_id].pop((qos_consts.RULE_TYPE_BANDWIDTH_LIMIT,
                                        constants.INGRESS_DIRECTION),
                                       None)
        if not port and not vif_port:
            LOG.debug("delete_bandwidth_limit_ingress was received "
                      "for port %s but port was not found. "
                      "It seems that bandwidth_limit is already deleted",
                      port_id)
            return
        vif_port = vif_port or port.get('vif_port')
        self.br_int.delete_ingress_bw_limit_for_port(vif_port.port_name)

    def create_dscp_marking(self, port, rule):
        self.update_dscp_marking(port, rule)

    def update_dscp_marking(self, port, rule):
        self.ports[port['port_id']][qos_consts.RULE_TYPE_DSCP_MARKING] = port
        vif_port = port.get('vif_port')
        if not vif_port:
            port_id = port.get('port_id')
            LOG.debug("update_dscp_marking was received for port %s but "
                      "vif_port was not found. It seems that port is already "
                      "deleted", port_id)
            return
        port = self.br_int.get_port_ofport(vif_port.port_name)
        self.br_int.install_dscp_marking_rule(port=port,
                                              dscp_mark=rule.dscp_mark)

    def delete_dscp_marking(self, port):
        vif_port = port.get('vif_port')
        dscp_port = self.ports[port['port_id']].pop(qos_consts.
                                                    RULE_TYPE_DSCP_MARKING, 0)

        if not dscp_port and not vif_port:
            LOG.debug("delete_dscp_marking was received for port %s but "
                      "no port information was stored to be deleted",
                      port['port_id'])
            return

        vif_port = vif_port or dscp_port.get('vif_port')
        port_num = vif_port.ofport
        self.br_int.uninstall_flows(in_port=port_num, table_id=0, reg2=0)

    def _update_egress_bandwidth_limit(self, vif_port, rule):
        max_kbps = rule.max_kbps
        # NOTE(slaweq): According to ovs docs:
        # http://openvswitch.org/support/dist-docs/ovs-vswitchd.conf.db.5.html
        # ovs accepts only integer values of burst:
        max_burst_kbps = int(self._get_egress_burst_value(rule))

        self.br_int.create_egress_bw_limit_for_port(vif_port.port_name,
                                                    max_kbps,
                                                    max_burst_kbps)

    def _update_ingress_bandwidth_limit(self, vif_port, rule):
        port_name = vif_port.port_name
        max_kbps = rule.max_kbps or 0
        max_burst_kbps = rule.max_burst_kbps or 0

        self.br_int.update_ingress_bw_limit_for_port(
            port_name,
            max_kbps,
            max_burst_kbps
        )

    def create_minimum_bandwidth(self, port, rule):
        self.update_minimum_bandwidth(port, rule)

    def update_minimum_bandwidth(self, port, rule):
        vif_port = port.get('vif_port')
        if not vif_port:
            LOG.debug('update_minimum_bandwidth was received for port %s but '
                      'vif_port was not found. It seems that port is already '
                      'deleted', port.get('port_id'))
            return

        self.ports[port['port_id']][(qos_consts.RULE_TYPE_MINIMUM_BANDWIDTH,
                                     rule.direction)] = port
        if rule.direction == constants.INGRESS_DIRECTION:
            LOG.debug('Minimum bandwidth ingress rule was updated/created for '
                      'port %s and rule %s.', port['port_id'], rule.id)
            return

        # queue_num is used to identify the port which traffic come from,
        # it needs to be unique across br-int. It is convenient to use ofport
        # as queue_num because it is unique in br-int and start from 1.
        egress_port_names = []
        for phy_br in self.agent_api.request_phy_brs():
            ports = phy_br.get_bridge_ports('')
            if not ports:
                LOG.warning('Bridge %s does not have a physical port '
                            'connected', phy_br.br_name)
            egress_port_names.extend(ports)
        qos_id = self.br_int.update_minimum_bandwidth_queue(
            port['port_id'], egress_port_names, vif_port.ofport, rule.min_kbps)
        for phy_br in self.agent_api.request_phy_brs():
            phy_br.set_queue_for_minimum_bandwidth(vif_port.ofport)
        LOG.debug('Minimum bandwidth egress rule was updated/created for port '
                  '%(port_id)s and rule %(rule_id)s. QoS ID: %(qos_id)s. '
                  'Egress ports with QoS applied: %(ports)s',
                  {'port_id': port['port_id'], 'rule_id': rule.id,
                   'qos_id': qos_id, 'ports': egress_port_names})

    def delete_minimum_bandwidth(self, port):
        rule_port = self.ports[port['port_id']].pop(
            (qos_consts.RULE_TYPE_MINIMUM_BANDWIDTH,
             constants.EGRESS_DIRECTION), None)
        if not rule_port:
            LOG.debug('delete_minimum_bandwidth was received for port %s but '
                      'no port information was stored to be deleted',
                      port['port_id'])
            return
        self.br_int.delete_minimum_bandwidth_queue(port['port_id'])
        LOG.debug("Minimum bandwidth rule was deleted for port: %s.",
                  port['port_id'])

    def delete_minimum_bandwidth_ingress(self, port):
        rule_port = self.ports[port['port_id']].pop(
            (qos_consts.RULE_TYPE_MINIMUM_BANDWIDTH,
             constants.INGRESS_DIRECTION), None)
        if not rule_port:
            LOG.debug('delete_minimum_bandwidth_ingress was received for port '
                      '%s but no port information was stored to be deleted',
                      port['port_id'])
            return
        LOG.debug("Minimum bandwidth rule for ingress direction was deleted "
                  "for port %s", port['port_id'])
