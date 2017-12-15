"""NFN Forwarder for PICN"""

import multiprocessing
import time

from PiCN.Layers.NFNLayer import BasicNFNLayer
from PiCN.Layers.ICNLayer import BasicICNLayer
from PiCN.Layers.ICNLayer.ForwardingInformationBase import ForwardingInformationBaseMemoryPrefix
from PiCN.Layers.ICNLayer.PendingInterestTable import PendingInterstTableMemoryExact
from PiCN.Layers.PacketEncodingLayer import BasicPacketEncodingLayer
from PiCN.Layers.NFNLayer.NFNEvaluator.NFNExecutor import NFNPythonExecutor
from PiCN.Layers.ICNLayer.ContentStore import ContentStoreMemoryExact
from PiCN.Layers.LinkLayer import UDP4LinkLayer
from PiCN.Layers.PacketEncodingLayer.Encoder import SimpleStringEncoder
from PiCN.Logger import Logger
from PiCN.Mgmt import Mgmt
from PiCN.Routing import BasicRouting

class NFNForwarder(object):
    """NFN Forwarder for PICN"""

    def __init__(self, port=9000, debug_level=255):
        # debug level
        logger = Logger("NFNForwarder", debug_level)
        logger.info("Start PiCN NFN Forwarder on port " + str(port))

        # packet encoder
        self.encoder = SimpleStringEncoder()

        # initialize layers
        self.linklayer = UDP4LinkLayer(port, debug_level=debug_level)
        self.packetencodinglayer = BasicPacketEncodingLayer(self.encoder, debug_level=debug_level)
        self.icnlayer = BasicICNLayer(debug_level=debug_level)

        # setup data structures
        self.cs = ContentStoreMemoryExact(self.icnlayer.manager)
        self.fib = ForwardingInformationBaseMemoryPrefix(self.icnlayer.manager)
        self.pit = PendingInterstTableMemoryExact(self.icnlayer.manager)

        self.icnlayer.cs = self.cs
        self.icnlayer.fib = self.fib
        self.icnlayer.pit = self.pit

        # setup nfn
        self.icnlayer._interest_to_app = True
        self.executors = {"PYTHON": NFNPythonExecutor}
        self.nfnlayer = BasicNFNLayer(self.icnlayer.manager, self.cs, self.fib, self.pit, self.executors,
                                      debug_level=debug_level)

        # setup communication queues
        self.q_link_packet_up = multiprocessing.Queue()
        self.q_packet_link_down = multiprocessing.Queue()

        self.q_packet_icn_up = multiprocessing.Queue()
        self.q_icn_packet_down = multiprocessing.Queue()

        self.q_routing_icn_up = multiprocessing.Queue()
        self.q_icn_routing_down = multiprocessing.Queue()

        self.q_icn_to_nfn = multiprocessing.Queue()
        self.q_nfn_to_icn = multiprocessing.Queue()

        # set link layer queues
        self.linklayer.queue_to_higher = self.q_link_packet_up
        self.linklayer.queue_from_higher = self.q_packet_link_down

        # set packet encoding layer queues
        self.packetencodinglayer.queue_to_lower = self.q_packet_link_down
        self.packetencodinglayer.queue_from_lower = self.q_link_packet_up
        self.packetencodinglayer.queue_to_higher = self.q_packet_icn_up
        self.packetencodinglayer.queue_from_higher = self.q_icn_packet_down

        # set icn layer queues
        self.icnlayer.queue_to_lower = self.q_icn_packet_down
        self.icnlayer.queue_from_lower = self.q_packet_icn_up
        self.icnlayer.queue_to_higher = self.q_icn_to_nfn
        self.icnlayer.queue_from_higher = self.q_nfn_to_icn

        # set nfn layer
        self.nfnlayer.queue_to_lower = self.q_nfn_to_icn
        self.nfnlayer.queue_from_lower = self.q_icn_to_nfn

        # routing
        self.routing = BasicRouting(self.icnlayer.pit, None, debug_level=debug_level)  # TODO NOT IMPLEMENTED YET

        # mgmt
        self.mgmt = Mgmt(self.cs, self.fib, self.pit, self.linklayer, port, self.stop_forwarder,
                         debug_level=debug_level)

    def start_forwarder(self):
        # start processes
        self.linklayer.start_process()
        self.packetencodinglayer.start_process()
        self.icnlayer.start_process()
        self.icnlayer.ageing()
        self.nfnlayer.start_process()
        self.mgmt.start_process()

    def stop_forwarder(self):
        # Stop processes
        self.mgmt.stop_process()
        self.linklayer.stop_process()
        self.packetencodinglayer.stop_process()
        self.icnlayer.stop_process()
        self.nfnlayer.stop_process()

        time.sleep(0.3)

        # close queues file descriptors
        self.q_link_packet_up.close()
        self.q_packet_link_down.close()
        self.q_packet_icn_up.close()
        self.q_icn_packet_down.close()
        self.q_nfn_to_icn.close()
        self.q_icn_to_nfn.close()