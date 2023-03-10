import xml.etree.ElementTree as ET
import settings

root = ET.Element("settings")

for name, value in vars(settings).items():
    if name.isupper():
        node = ET.SubElement(root, name)
        node.text = str(value)

tree = ET.ElementTree(root)
tree.write("settings.xml")
