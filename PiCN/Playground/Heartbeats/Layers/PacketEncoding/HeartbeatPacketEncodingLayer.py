import multiprocessing
from PiCN.Playground.Heartbeats.Layers.PacketEncoding import ExtendedNdnTlvEncoder
from PiCN.Processes import LayerProcess


class HeartbeatPacketEncodingLayer(LayerProcess):
    def __init__(self, encoder: ExtendedNdnTlvEncoder = None, log_level=255):
        LayerProcess.__init__(self, logger_name="PktEncLayer", log_level=log_level)
        self._encoder: ExtendedNdnTlvEncoder = encoder

    @property
    def encoder(self):
        return self._encoder

    @encoder.setter
    def encoder(self, encoder):
        self._encoder = encoder

    def data_from_higher(self, to_lower: multiprocessing.Queue, to_higher: multiprocessing.Queue, data):
        face_id, packet = self.check_data(data)
        if face_id == None or packet is None:
            return
        encoded_packet = self.encode(packet)
        if encoded_packet is None:
            self.logger.info("Dropping Packet since None")
            return
        to_lower.put([face_id, encoded_packet])

    def data_from_lower(self, to_lower: multiprocessing.Queue, to_higher: multiprocessing.Queue, data):
        face_id, packet = self.check_data(data)
        if face_id == None or packet == None:
            return
        decoded_packet = self.decode(packet)
        if decoded_packet is None:
            self.logger.info("Dropping Packet since None")
            return
        to_higher.put([face_id, decoded_packet])

    def encode(self, data):
        self.logger.info("Encode packet")
        return self._encoder.encode(data)

    def decode(self, data):
        self.logger.info("Decode packet")
        return self._encoder.decode(data)

    def check_data(self, data):
        """check if data from queue match the requirements"""
        if len(data) != 2:
            self.logger.warning("PacketEncoding Layer expects queue elements to have size 2")
            return (None, None)
        if type(data[0]) != int:
            self.logger.warning("PacketEncoding Layer expects first element to be a faceid (int)")
            return (None, None)
        # TODO test if data[1] has type packet or bin data? howto?
        return data[0], data[1]
