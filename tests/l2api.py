# DELL/Force10 Devices
import netl2api.l2api.dell.force10
sw = netl2api.l2api.dell.force10.Force10(host="10.0.0.1", username="l2apiusername", passwd="p4zz")
sw.show_system()


# HP/Flex10 Devices
import netl2api.l2api.hp.flex10
sw = netl2api.l2api.hp.flex10.Flex10(host="10.0.0.2", username="l2apiusername", passwd="p4zz")
sw.show_system()
