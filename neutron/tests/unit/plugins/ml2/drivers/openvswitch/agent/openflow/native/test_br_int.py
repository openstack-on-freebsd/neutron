# Copyright (C) 2014,2015 VA Linux Systems Japan K.K.
# Copyright (C) 2014,2015 YAMAMOTO Takashi <yamamoto at valinux co jp>
# All Rights Reserved.
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

from unittest import mock

from neutron_lib import constants as p_const

from neutron.plugins.ml2.drivers.openvswitch.agent.common import constants
from neutron.tests.unit.plugins.ml2.drivers.openvswitch.agent.openflow.native \
    import ovs_bridge_test_base


call = mock.call  # short hand


class OVSIntegrationBridgeTest(ovs_bridge_test_base.OVSBridgeTestBase):
    def setUp(self):
        super(OVSIntegrationBridgeTest, self).setUp()
        self.setup_bridge_mock('br-int', self.br_int_cls)
        self.stamp = self.br.default_cookie

    def test_setup_default_table(self):
        self.br.setup_default_table(enable_openflow_dhcp=True,
                                    enable_dhcpv6=True)
        (dp, ofp, ofpp) = self._get_dp()
        expected = [
            call._send_msg(ofpp.OFPFlowMod(dp,
                cookie=self.stamp,
                instructions=[],
                match=ofpp.OFPMatch(),
                priority=0,
                table_id=23),
                           active_bundle=None),
            call._send_msg(ofpp.OFPFlowMod(dp,
                cookie=self.stamp,
                instructions=[
                    ofpp.OFPInstructionGotoTable(table_id=60),
                ],
                match=ofpp.OFPMatch(),
                priority=0,
                table_id=0),
                           active_bundle=None),
            call._send_msg(ofpp.OFPFlowMod(dp,
                cookie=self.stamp,
                instructions=[
                    ofpp.OFPInstructionActions(
                        ofp.OFPIT_APPLY_ACTIONS, [
                            ofpp.OFPActionOutput(ofp.OFPP_NORMAL, 0)
                        ]),
                ],
                match=ofpp.OFPMatch(),
                priority=3,
                table_id=60),
                           active_bundle=None),
            call._send_msg(ofpp.OFPFlowMod(dp,
                cookie=self.stamp,
                instructions=[ofpp.OFPInstructionGotoTable(table_id=77)],
                match=ofpp.OFPMatch(eth_type=self.ether_types.ETH_TYPE_IP,
                                    ip_proto=self.in_proto.IPPROTO_UDP,
                                    ipv4_dst="255.255.255.255",
                                    udp_dst=67,
                                    udp_src=68),
                priority=101,
                table_id=60),
                           active_bundle=None),
            call._send_msg(ofpp.OFPFlowMod(dp,
                cookie=self.stamp,
                instructions=[],
                match=ofpp.OFPMatch(),
                priority=0,
                table_id=77),
                           active_bundle=None),
            call._send_msg(ofpp.OFPFlowMod(dp,
                cookie=self.stamp,
                instructions=[ofpp.OFPInstructionGotoTable(table_id=78)],
                match=ofpp.OFPMatch(eth_type=self.ether_types.ETH_TYPE_IPV6,
                                    ip_proto=self.in_proto.IPPROTO_UDP,
                                    ipv6_dst="ff02::1:2",
                                    udp_dst=547,
                                    udp_src=546),
                priority=101,
                table_id=60),
                           active_bundle=None),
            call._send_msg(ofpp.OFPFlowMod(dp,
                cookie=self.stamp,
                instructions=[],
                match=ofpp.OFPMatch(),
                priority=0,
                table_id=78),
                           active_bundle=None),
            call._send_msg(ofpp.OFPFlowMod(dp,
                cookie=self.stamp,
                instructions=[],
                match=ofpp.OFPMatch(),
                priority=0,
                table_id=24),
                           active_bundle=None),
            call._send_msg(ofpp.OFPFlowMod(dp,
                cookie=self.stamp,
                instructions=[],
                match=ofpp.OFPMatch(vlan_vid=ofp.OFPVID_PRESENT | 4095),
                priority=65535,
                table_id=0),
                           active_bundle=None),
            call._send_msg(ofpp.OFPFlowMod(dp,
                cookie=self.stamp,
                instructions=[
                    ofpp.OFPInstructionActions(
                        ofp.OFPIT_APPLY_ACTIONS, [
                            ofpp.OFPActionOutput(ofp.OFPP_NORMAL, 0)
                        ]),
                ],
                match=ofpp.OFPMatch(),
                priority=3,
                table_id=constants.TRANSIENT_EGRESS_TABLE),
                           active_bundle=None),
        ]
        self.assertEqual(expected, self.mock.mock_calls)

    def test_provision_local_vlan(self):
        port = 999
        lvid = 888
        segmentation_id = 777
        self.br.provision_local_vlan(port=port, lvid=lvid,
                                     segmentation_id=segmentation_id)
        (dp, ofp, ofpp) = self._get_dp()
        expected = [
            call._send_msg(ofpp.OFPFlowMod(dp,
                cookie=self.stamp,
                instructions=[
                    ofpp.OFPInstructionActions(ofp.OFPIT_APPLY_ACTIONS, [
                        ofpp.OFPActionSetField(
                            vlan_vid=lvid | ofp.OFPVID_PRESENT),
                    ]),
                    ofpp.OFPInstructionGotoTable(table_id=60),
                ],
                match=ofpp.OFPMatch(
                    in_port=port,
                    vlan_vid=segmentation_id | ofp.OFPVID_PRESENT),
                priority=3,
                table_id=0),
                           active_bundle=None),
        ]
        self.assertEqual(expected, self.mock.mock_calls)

    def test_provision_local_vlan_novlan(self):
        port = 999
        lvid = 888
        segmentation_id = None
        self.br.provision_local_vlan(port=port, lvid=lvid,
                                     segmentation_id=segmentation_id)
        (dp, ofp, ofpp) = self._get_dp()
        expected = [
            call._send_msg(ofpp.OFPFlowMod(dp,
                cookie=self.stamp,
                instructions=[
                    ofpp.OFPInstructionActions(ofp.OFPIT_APPLY_ACTIONS, [
                        ofpp.OFPActionPushVlan(),
                        ofpp.OFPActionSetField(
                            vlan_vid=lvid | ofp.OFPVID_PRESENT),
                    ]),
                    ofpp.OFPInstructionGotoTable(table_id=60),
                ],
                match=ofpp.OFPMatch(
                    in_port=port,
                    vlan_vid=ofp.OFPVID_NONE),
                priority=3,
                table_id=0),
                           active_bundle=None),
        ]
        self.assertEqual(expected, self.mock.mock_calls)

    def test_reclaim_local_vlan(self):
        port = 999
        segmentation_id = 777
        self.br.reclaim_local_vlan(port=port, segmentation_id=segmentation_id)
        (dp, ofp, ofpp) = self._get_dp()
        expected = [
            call.uninstall_flows(
                match=ofpp.OFPMatch(
                    in_port=port,
                    vlan_vid=segmentation_id | ofp.OFPVID_PRESENT)),
        ]
        self.assertEqual(expected, self.mock.mock_calls)

    def test_reclaim_local_vlan_novlan(self):
        port = 999
        segmentation_id = None
        self.br.reclaim_local_vlan(port=port, segmentation_id=segmentation_id)
        (dp, ofp, ofpp) = self._get_dp()
        expected = [
            call.uninstall_flows(
                match=ofpp.OFPMatch(
                    in_port=port,
                    vlan_vid=ofp.OFPVID_NONE)),
        ]
        self.assertEqual(expected, self.mock.mock_calls)

    def test_install_dvr_to_src_mac(self):
        network_type = 'vxlan'
        vlan_tag = 1111
        gateway_mac = '08:60:6e:7f:74:e7'
        dst_mac = '00:02:b3:13:fe:3d'
        dst_port = 6666
        self.br.install_dvr_to_src_mac(network_type=network_type,
                                       vlan_tag=vlan_tag,
                                       gateway_mac=gateway_mac,
                                       dst_mac=dst_mac,
                                       dst_port=dst_port)
        (dp, ofp, ofpp) = self._get_dp()
        expected = [
            call._send_msg(ofpp.OFPFlowMod(dp,
                cookie=self.stamp,
                instructions=[
                    ofpp.OFPInstructionActions(ofp.OFPIT_APPLY_ACTIONS, [
                        ofpp.OFPActionSetField(eth_src=gateway_mac),
                    ]),
                    ofpp.OFPInstructionGotoTable(table_id=60),
                ],
                match=ofpp.OFPMatch(
                    eth_dst=dst_mac,
                    vlan_vid=vlan_tag | ofp.OFPVID_PRESENT),
                priority=20,
                table_id=1),
                           active_bundle=None),
            call._send_msg(ofpp.OFPFlowMod(dp,
                cookie=self.stamp,
                instructions=[
                    ofpp.OFPInstructionActions(ofp.OFPIT_APPLY_ACTIONS, [
                        ofpp.OFPActionPopVlan(),
                        ofpp.OFPActionOutput(6666, 0),
                    ]),
                ],
                match=ofpp.OFPMatch(
                    eth_dst=dst_mac,
                    vlan_vid=vlan_tag | ofp.OFPVID_PRESENT),
                priority=20,
                table_id=60),
                           active_bundle=None),
        ]
        self.assertEqual(expected, self.mock.mock_calls)

    def test_delete_dvr_to_src_mac(self):
        network_type = 'vxlan'
        vlan_tag = 1111
        dst_mac = '00:02:b3:13:fe:3d'
        self.br.delete_dvr_to_src_mac(network_type=network_type,
                                      vlan_tag=vlan_tag,
                                      dst_mac=dst_mac)
        (dp, ofp, ofpp) = self._get_dp()
        expected = [
            call.uninstall_flows(
                strict=True,
                priority=20,
                table_id=1,
                match=ofpp.OFPMatch(
                    eth_dst=dst_mac,
                    vlan_vid=vlan_tag | ofp.OFPVID_PRESENT)),
            call.uninstall_flows(
                strict=True,
                priority=20,
                table_id=60,
                match=ofpp.OFPMatch(
                    eth_dst=dst_mac,
                    vlan_vid=vlan_tag | ofp.OFPVID_PRESENT)),
        ]
        self.assertEqual(expected, self.mock.mock_calls)

    def test_install_dvr_to_src_mac_vlan(self):
        network_type = 'vlan'
        vlan_tag = 1111
        gateway_mac = '08:60:6e:7f:74:e7'
        dst_mac = '00:02:b3:13:fe:3d'
        dst_port = 6666
        self.br.install_dvr_to_src_mac(network_type=network_type,
                                       vlan_tag=vlan_tag,
                                       gateway_mac=gateway_mac,
                                       dst_mac=dst_mac,
                                       dst_port=dst_port)
        (dp, ofp, ofpp) = self._get_dp()
        expected = [
            call._send_msg(ofpp.OFPFlowMod(dp,
                cookie=self.stamp,
                instructions=[
                    ofpp.OFPInstructionActions(ofp.OFPIT_APPLY_ACTIONS, [
                        ofpp.OFPActionSetField(eth_src=gateway_mac),
                    ]),
                    ofpp.OFPInstructionGotoTable(table_id=60),
                ],
                match=ofpp.OFPMatch(
                    eth_dst=dst_mac,
                    vlan_vid=vlan_tag | ofp.OFPVID_PRESENT),
                priority=20,
                table_id=2),
                           active_bundle=None),
            call._send_msg(ofpp.OFPFlowMod(dp,
                cookie=self.stamp,
                instructions=[
                    ofpp.OFPInstructionActions(ofp.OFPIT_APPLY_ACTIONS, [
                        ofpp.OFPActionPopVlan(),
                        ofpp.OFPActionOutput(dst_port, 0),
                    ]),
                ],
                match=ofpp.OFPMatch(
                    eth_dst=dst_mac,
                    vlan_vid=vlan_tag | ofp.OFPVID_PRESENT),
                priority=20,
                table_id=60),
                           active_bundle=None),
        ]
        self.assertEqual(expected, self.mock.mock_calls)

    def test_install_dvr_to_src_mac_flat(self):
        network_type = 'flat'
        gateway_mac = '08:60:6e:7f:74:e7'
        dst_mac = '00:02:b3:13:fe:3d'
        dst_port = 6666
        self.br.install_dvr_to_src_mac(network_type=network_type,
                                       vlan_tag=None,
                                       gateway_mac=gateway_mac,
                                       dst_mac=dst_mac,
                                       dst_port=dst_port)
        (dp, ofp, ofpp) = self._get_dp()
        expected = [
            call._send_msg(ofpp.OFPFlowMod(dp,
                cookie=self.stamp,
                instructions=[
                    ofpp.OFPInstructionActions(ofp.OFPIT_APPLY_ACTIONS, [
                        ofpp.OFPActionSetField(eth_src=gateway_mac),
                    ]),
                    ofpp.OFPInstructionGotoTable(table_id=60),
                ],
                match=ofpp.OFPMatch(
                    eth_dst=dst_mac,
                    vlan_vid=ofp.OFPVID_NONE),
                priority=20,
                table_id=2),
                           active_bundle=None),
            call._send_msg(ofpp.OFPFlowMod(dp,
                cookie=self.stamp,
                instructions=[
                    ofpp.OFPInstructionActions(ofp.OFPIT_APPLY_ACTIONS, [
                        ofpp.OFPActionOutput(dst_port, 0),
                    ]),
                ],
                match=ofpp.OFPMatch(
                    eth_dst=dst_mac,
                    vlan_vid=ofp.OFPVID_NONE),
                priority=20,
                table_id=60),
                           active_bundle=None),
        ]
        self.assertEqual(expected, self.mock.mock_calls)

    def test_delete_dvr_to_src_mac_vlan(self):
        network_type = 'vlan'
        vlan_tag = 1111
        dst_mac = '00:02:b3:13:fe:3d'
        self.br.delete_dvr_to_src_mac(network_type=network_type,
                                      vlan_tag=vlan_tag,
                                      dst_mac=dst_mac)
        (dp, ofp, ofpp) = self._get_dp()
        expected = [
            call.uninstall_flows(
                strict=True,
                priority=20,
                table_id=2,
                match=ofpp.OFPMatch(
                    eth_dst=dst_mac,
                    vlan_vid=vlan_tag | ofp.OFPVID_PRESENT)),
            call.uninstall_flows(
                strict=True,
                priority=20,
                table_id=60,
                match=ofpp.OFPMatch(
                    eth_dst=dst_mac,
                    vlan_vid=vlan_tag | ofp.OFPVID_PRESENT)),
        ]
        self.assertEqual(expected, self.mock.mock_calls)

    def test_delete_dvr_to_src_mac_flat(self):
        network_type = 'flat'
        vlan_tag = None
        dst_mac = '00:02:b3:13:fe:3d'
        self.br.delete_dvr_to_src_mac(network_type=network_type,
                                      vlan_tag=vlan_tag,
                                      dst_mac=dst_mac)
        (dp, ofp, ofpp) = self._get_dp()
        expected = [
            call.uninstall_flows(
                strict=True,
                priority=20,
                table_id=2,
                match=ofpp.OFPMatch(
                    eth_dst=dst_mac,
                    vlan_vid=ofp.OFPVID_NONE)),
            call.uninstall_flows(
                strict=True,
                priority=20,
                table_id=60,
                match=ofpp.OFPMatch(
                    eth_dst=dst_mac,
                    vlan_vid=ofp.OFPVID_NONE)),
        ]
        self.assertEqual(expected, self.mock.mock_calls)

    def test_add_dvr_mac_physical(self):
        mac = '00:02:b3:13:fe:3d'
        port = 8888
        self.br.add_dvr_mac_physical(mac=mac, port=port)
        (dp, ofp, ofpp) = self._get_dp()
        expected = [
            call._send_msg(ofpp.OFPFlowMod(dp,
                cookie=self.stamp,
                instructions=[
                    ofpp.OFPInstructionGotoTable(table_id=2),
                ],
                match=ofpp.OFPMatch(
                    eth_src=mac,
                    in_port=port),
                priority=4,
                table_id=0),
                           active_bundle=None)
        ]
        self.assertEqual(expected, self.mock.mock_calls)

    def test_remove_dvr_mac_vlan(self):
        mac = '00:02:b3:13:fe:3d'
        self.br.remove_dvr_mac_vlan(mac=mac)
        (dp, ofp, ofpp) = self._get_dp()
        expected = [
            call.uninstall_flows(eth_src=mac, table_id=0),
        ]
        self.assertEqual(expected, self.mock.mock_calls)

    def test_add_dvr_mac_tun(self):
        mac = '00:02:b3:13:fe:3d'
        port = 8888
        self.br.add_dvr_mac_tun(mac=mac, port=port)
        (dp, ofp, ofpp) = self._get_dp()
        expected = [
            call._send_msg(ofpp.OFPFlowMod(dp,
                cookie=self.stamp,
                instructions=[
                    ofpp.OFPInstructionGotoTable(table_id=1),
                ],
                match=ofpp.OFPMatch(
                    eth_src=mac,
                    in_port=port),
                priority=2,
                table_id=0),
                           active_bundle=None)
        ]
        self.assertEqual(expected, self.mock.mock_calls)

    def test_remove_dvr_mac_tun(self):
        mac = '00:02:b3:13:fe:3d'
        port = 8888
        self.br.remove_dvr_mac_tun(mac=mac, port=port)
        expected = [
            call.uninstall_flows(eth_src=mac, in_port=port, table_id=0),
        ]
        self.assertEqual(expected, self.mock.mock_calls)

    def test_install_icmpv6_na_spoofing_protection(self):
        port = 8888
        ip_addresses = ['2001:db8::1', 'fdf8:f53b:82e4::1/128']
        self.br.install_icmpv6_na_spoofing_protection(port, ip_addresses)
        (dp, ofp, ofpp) = self._get_dp()
        expected = [
            call._send_msg(ofpp.OFPFlowMod(dp,
                cookie=self.stamp,
                instructions=[
                    ofpp.OFPInstructionGotoTable(table_id=60),
                ],
                match=ofpp.OFPMatch(
                    eth_type=self.ether_types.ETH_TYPE_IPV6,
                    icmpv6_type=self.icmpv6.ND_NEIGHBOR_ADVERT,
                    ip_proto=self.in_proto.IPPROTO_ICMPV6,
                    ipv6_nd_target='2001:db8::1',
                    in_port=8888,
                ),
                priority=2,
                table_id=24),
                           active_bundle=None),
            call._send_msg(ofpp.OFPFlowMod(dp,
                cookie=self.stamp,
                instructions=[
                    ofpp.OFPInstructionGotoTable(table_id=60),
                ],
                match=ofpp.OFPMatch(
                    eth_type=self.ether_types.ETH_TYPE_IPV6,
                    icmpv6_type=self.icmpv6.ND_NEIGHBOR_ADVERT,
                    ip_proto=self.in_proto.IPPROTO_ICMPV6,
                    ipv6_nd_target='fdf8:f53b:82e4::1',
                    in_port=8888,
                ),
                priority=2,
                table_id=24),
                           active_bundle=None),
            call._send_msg(ofpp.OFPFlowMod(dp,
                cookie=self.stamp,
                instructions=[
                    ofpp.OFPInstructionGotoTable(table_id=24),
                ],
                match=ofpp.OFPMatch(
                    eth_type=self.ether_types.ETH_TYPE_IPV6,
                    icmpv6_type=self.icmpv6.ND_NEIGHBOR_ADVERT,
                    ip_proto=self.in_proto.IPPROTO_ICMPV6,
                    in_port=8888,
                ),
                priority=10,
                table_id=0),
                           active_bundle=None),
        ]
        self.assertEqual(expected, self.mock.mock_calls)

    def test_install_arp_spoofing_protection(self):
        port = 8888
        ip_addresses = ['192.0.2.1', '192.0.2.2/32']
        self.br.install_arp_spoofing_protection(port, ip_addresses)
        (dp, ofp, ofpp) = self._get_dp()
        expected = [
            call._send_msg(ofpp.OFPFlowMod(dp,
                cookie=self.stamp,
                instructions=[
                    ofpp.OFPInstructionGotoTable(table_id=25),
                ],
                match=ofpp.OFPMatch(
                    eth_type=self.ether_types.ETH_TYPE_ARP,
                    arp_spa='192.0.2.1',
                    in_port=8888,
                ),
                priority=2,
                table_id=24),
                           active_bundle=None),
            call._send_msg(ofpp.OFPFlowMod(dp,
                cookie=self.stamp,
                instructions=[
                    ofpp.OFPInstructionGotoTable(table_id=25),
                ],
                match=ofpp.OFPMatch(
                    eth_type=self.ether_types.ETH_TYPE_ARP,
                    arp_spa='192.0.2.2',
                    in_port=8888
                ),
                priority=2,
                table_id=24),
                           active_bundle=None),
            call._send_msg(ofpp.OFPFlowMod(dp,
                cookie=self.stamp,
                instructions=[
                    ofpp.OFPInstructionGotoTable(table_id=24),
                ],
                match=ofpp.OFPMatch(
                    eth_type=self.ether_types.ETH_TYPE_ARP,
                    in_port=8888,
                ),
                priority=10,
                table_id=0),
                           active_bundle=None),
        ]
        self.assertEqual(expected, self.mock.mock_calls)

    def test_delete_arp_spoofing_protection(self):
        port = 8888
        self.br.delete_arp_spoofing_protection(port)
        (dp, ofp, ofpp) = self._get_dp()
        expected = [
            call.uninstall_flows(table_id=0, match=ofpp.OFPMatch(
                eth_type=self.ether_types.ETH_TYPE_ARP,
                in_port=8888)),
            call.uninstall_flows(table_id=0, match=ofpp.OFPMatch(
                eth_type=self.ether_types.ETH_TYPE_IPV6,
                icmpv6_type=self.icmpv6.ND_NEIGHBOR_ADVERT,
                in_port=8888,
                ip_proto=self.in_proto.IPPROTO_ICMPV6)),
            call.uninstall_flows(table_id=24, in_port=port),
        ]
        self.assertEqual(expected, self.mock.mock_calls)

    def _test_delete_dvr_dst_mac_for_arp(self, network_type):
        if network_type in (p_const.TYPE_VLAN, p_const.TYPE_FLAT):
            table_id = constants.DVR_TO_SRC_MAC_PHYSICAL
        else:
            table_id = constants.DVR_TO_SRC_MAC

        if network_type == p_const.TYPE_FLAT:
            vlan_tag = None
        else:
            vlan_tag = 1111
        gateway_mac = '00:02:b3:13:fe:3e'
        dvr_mac = '00:02:b3:13:fe:3f'
        rtr_port = 8888
        self.br.delete_dvr_dst_mac_for_arp(network_type=network_type,
                                           vlan_tag=vlan_tag,
                                           gateway_mac=gateway_mac,
                                           dvr_mac=dvr_mac,
                                           rtr_port=rtr_port)
        (dp, ofp, ofpp) = self._get_dp()
        if network_type == p_const.TYPE_FLAT:
            expected = [
                call.uninstall_flows(
                    strict=True,
                    priority=5,
                    table_id=table_id,
                    match=ofpp.OFPMatch(
                        eth_dst=dvr_mac,
                        vlan_vid=ofp.OFPVID_NONE)),
            ]
        else:
            expected = [
                call.uninstall_flows(
                    strict=True,
                    priority=5,
                    table_id=table_id,
                    match=ofpp.OFPMatch(
                        eth_dst=dvr_mac,
                        vlan_vid=vlan_tag | ofp.OFPVID_PRESENT)),
            ]
        self.assertEqual(expected, self.mock.mock_calls)

    def test_delete_dvr_dst_mac_for_arp_vlan(self):
        self._test_delete_dvr_dst_mac_for_arp(network_type='vlan')

    def test_delete_dvr_dst_mac_for_arp_tunnel(self):
        self._test_delete_dvr_dst_mac_for_arp(network_type='vxlan')

    def test_delete_dvr_dst_mac_for_flat(self):
        self._test_delete_dvr_dst_mac_for_arp(network_type='flat')

    def test_install_dscp_marking_rule(self):
        test_port = 8888
        test_mark = 38
        self.br.install_dscp_marking_rule(port=test_port, dscp_mark=test_mark)

        (dp, ofp, ofpp) = self._get_dp()
        expected = [
            call._send_msg(ofpp.OFPFlowMod(dp, cookie=self.br.default_cookie,
                           instructions=[ofpp.OFPInstructionActions(
                               ofp.OFPIT_APPLY_ACTIONS,
                               [ofpp.OFPActionSetField(reg2=1),
                                ofpp.OFPActionSetField(ip_dscp=38),
                                ofpp.NXActionResubmit(in_port=8888)])],
                               match=ofpp.OFPMatch(eth_type=0x0800,
                                                   in_port=8888, reg2=0),
                               priority=65535, table_id=0),
                           active_bundle=None),
            call._send_msg(ofpp.OFPFlowMod(dp, cookie=self.br.default_cookie,
                           instructions=[ofpp.OFPInstructionActions(
                               ofp.OFPIT_APPLY_ACTIONS,
                               [ofpp.OFPActionSetField(reg2=1),
                                ofpp.OFPActionSetField(ip_dscp=38),
                                ofpp.NXActionResubmit(in_port=8888)])],
                               match=ofpp.OFPMatch(eth_type=0x86DD,
                                                   in_port=8888, reg2=0),
                               priority=65535, table_id=0),
                           active_bundle=None)
        ]
        self.assertEqual(expected, self.mock.mock_calls)
