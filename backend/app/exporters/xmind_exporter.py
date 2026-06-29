"""XMind 测试用例导出器。

基于旧工具 `scripts/generate_xmind.py` 的实现迁移，保留标准库生成 `.xmind`
zip 包的方式，便于后端直接调用。
"""

import hashlib
import time
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET
from xml.etree.ElementTree import Element, SubElement

from app.ai.models import TestCaseItem
from app.exporters.adapters import to_legacy_cases


class XmindExporter:
    def __init__(self):
        self._id_counter = 0

    def export(
        self,
        cases: list[TestCaseItem],
        output_path: str | Path,
        root_title: str = "测试用例",
    ) -> Path:
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)

        legacy_cases = to_legacy_cases(cases)
        content_xml = self._build_xmind_content(legacy_cases, root_title)
        manifest_xml = self._build_manifest()

        with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("content.xml", content_xml)
            zf.writestr("META-INF/manifest.xml", manifest_xml)

        return output

    def _new_id(self, text: str = "") -> str:
        self._id_counter += 1
        raw = f"{text}{self._id_counter}{time.time()}"
        return hashlib.md5(raw.encode()).hexdigest()[:26]

    @staticmethod
    def _ts() -> str:
        return str(int(time.time() * 1000))

    def _make_topic(self, parent: Element, title: str) -> Element:
        children = parent.find("children")
        if children is None:
            children = SubElement(parent, "children")

        topics = children.find("topics[@type='attached']")
        if topics is None:
            topics = SubElement(children, "topics", attrib={"type": "attached"})

        topic = SubElement(
            topics,
            "topic",
            attrib={"id": self._new_id(title), "timestamp": self._ts()},
        )
        SubElement(topic, "title").text = title
        return topic

    def _build_module_path(self, root_topic: Element, module_path: list[str]) -> Element:
        if len(module_path) > 8:
            raise ValueError(f"模块层数超过8层: {module_path}")

        current = root_topic
        for module_name in module_path:
            found = None
            children = current.find("children")
            if children is not None:
                topics = children.find("topics[@type='attached']")
                if topics is not None:
                    for topic in topics.findall("topic"):
                        title_el = topic.find("title")
                        if title_el is not None and title_el.text == module_name:
                            found = topic
                            break
            current = found if found is not None else self._make_topic(current, module_name)
        return current

    def _build_test_case(self, parent: Element, case: dict):
        title = str(case.get("用例标题") or "").strip()
        if not title:
            return

        priority = str(case.get("优先级") or "").strip().upper()
        tc_title = f"tc-{priority.lower()}: {title}" if priority in {"P0", "P1", "P2", "P3"} else f"tc: {title}"
        tc_node = self._make_topic(parent, tc_title)

        precondition = str(case.get("前置条件") or "").strip()
        if precondition:
            self._make_topic(tc_node, f"pc: {precondition}")

        for step in case.get("步骤") or []:
            action = str(step.get("操作") or step.get("步骤") or "").strip()
            expected = str(step.get("预期") or step.get("预期结果") or "").strip()
            if not action:
                continue
            step_node = self._make_topic(tc_node, action)
            if expected:
                self._make_topic(step_node, expected)

        remark = str(case.get("备注") or "").strip()
        if remark:
            self._make_topic(tc_node, f"rc: {remark}")

        tag = str(case.get("标签") or "").strip()
        if tag:
            self._make_topic(tc_node, f"tag:{tag}")

    def _build_xmind_content(self, cases: list[dict], root_title: str) -> bytes:
        xmap = Element(
            "xmap-content",
            attrib={
                "version": "2.0",
                "xmlns": "urn:xmind:xmap:xmlns:content:2.0",
                "xmlns:fo": "http://www.w3.org/1999/XSL/Format",
                "xmlns:svg": "http://www.w3.org/2000/svg",
                "xmlns:xhtml": "http://www.w3.org/1999/xhtml",
                "xmlns:xlink": "http://www.w3.org/1999/xlink",
            },
        )

        sheet = SubElement(xmap, "sheet", attrib={"id": self._new_id("sheet"), "timestamp": self._ts()})
        root_topic = SubElement(sheet, "topic", attrib={"id": self._new_id(root_title), "timestamp": self._ts()})
        SubElement(root_topic, "title").text = root_title
        SubElement(sheet, "title").text = "Sheet 1"

        for case in cases:
            module_path = case.get("模块") or []
            if isinstance(module_path, str):
                module_path = [module_path]
            parent = self._build_module_path(root_topic, module_path) if module_path else root_topic
            self._build_test_case(parent, case)

        ET.indent(xmap, space="  ")
        return ET.tostring(xmap, encoding="unicode", xml_declaration=False).encode("utf-8")

    @staticmethod
    def _build_manifest() -> bytes:
        manifest = Element("manifest", attrib={"xmlns": "urn:xmind:xmap:xmlns:manifest:1.0"})
        SubElement(manifest, "file-entry", attrib={"full-path": "content.xml", "media-type": "text/xml"})
        SubElement(manifest, "file-entry", attrib={"full-path": "META-INF/", "media-type": ""})
        ET.indent(manifest, space="  ")
        return ET.tostring(manifest, encoding="unicode").encode("utf-8")
