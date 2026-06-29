"""需求来源读取器。

迁移旧工具 Phase 1 的能力：读取 `requirements/` 下的 Markdown/TXT 文件，
并识别图片资产，供后续文档解析或多模态模型使用。
"""

from dataclasses import dataclass
from pathlib import Path


TEXT_EXTENSIONS = {".md", ".markdown", ".txt"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".svg"}


@dataclass(frozen=True)
class RequirementAsset:
    path: Path
    asset_type: str
    name: str
    suffix: str


class RequirementReader:
    def read_directory(self, requirements_dir: str | Path) -> tuple[str, list[RequirementAsset]]:
        directory = Path(requirements_dir)
        if not directory.exists():
            raise FileNotFoundError(f"需求目录不存在: {directory}")
        if not directory.is_dir():
            raise NotADirectoryError(f"不是有效需求目录: {directory}")

        text_parts: list[str] = []
        assets: list[RequirementAsset] = []

        for path in sorted(directory.iterdir(), key=lambda item: item.name):
            if not path.is_file():
                continue
            suffix = path.suffix.lower()
            if suffix in TEXT_EXTENSIONS:
                text_parts.append(f"<!-- source: {path.name} -->\n{path.read_text(encoding='utf-8')}")
                assets.append(self._asset(path, "text"))
            elif suffix in IMAGE_EXTENSIONS:
                assets.append(self._asset(path, "image"))

        return "\n\n---\n\n".join(text_parts).strip(), assets

    @staticmethod
    def _asset(path: Path, asset_type: str) -> RequirementAsset:
        return RequirementAsset(
            path=path,
            asset_type=asset_type,
            name=path.name,
            suffix=path.suffix.lower(),
        )
