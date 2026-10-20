"""
PyDiagram - Aplicativo de Diagramação Open-Source
Inspirado no StarUML | Construído com Python e PyQt6

Módulo Principal (main.py): Orquestração da Janela Principal e Ponto de Entrada.
"""

from __future__ import annotations
import json
import math
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from PyQt6.QtCore import QPointF, QRectF, Qt, QTimer
from PyQt6.QtGui import (
    QAction,
    QActionGroup,
    QColor,
    QFont,
    QImage,
    QPainter,
)
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QColorDialog,
    QComboBox,
    QDockWidget,
    QFileDialog,
    QFontComboBox,
    QFormLayout,
    QGroupBox,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QSplitter,
    QStatusBar,
    QToolBar,
    QToolButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
)

# Importações dos módulos gráficos e de componentes
from uml_items import (
    AnchorItem,
    ConnectionAnchorItem,
    ConnectionConfigDialog,
    DiagramConnectionItem,
    DiagramNodeItem,
    EditableTextItem,
    FloatingEditPanel,
    InlineActionPanel,
    UMLMemberItem,
    WaypointItem,
    get_main_window,
)
from ui_components import (
    DiagramScene,
    DiagramView,
    MinimapView,
)

# Re-exportações para compatibilidade reversa com scripts e testes existentes
__all__ = [
    "get_resource_path",
    "load_languages",
    "I18nManager",
    "AnchorItem",
    "ConnectionAnchorItem",
    "ConnectionConfigDialog",
    "DiagramConnectionItem",
    "EditableTextItem",
    "InlineActionPanel",
    "FloatingEditPanel",
    "DiagramNodeItem",
    "UMLMemberItem",
    "WaypointItem",
    "DiagramScene",
    "DiagramView",
    "MinimapView",
    "MainWindow",
    "get_main_window",
    "main",
]


# ==============================================================================
# 1. Utilitário de Caminho Base (PyInstaller) e Internacionalização (i18n)
# ==============================================================================
def get_base_path() -> str:
    """
    Deteta o caminho base do programa:
    - Se compilado (frozen), retorna a pasta física do executável: os.path.dirname(sys.executable).
    - Caso contrário (.py), retorna os.path.abspath(os.path.dirname(__file__)).
    """
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.abspath(os.path.dirname(__file__))


def get_resource_path(relative_path: str = "") -> str:
    """
    Retorna o caminho absoluto ao lado do executável (quando compilado com PyInstaller)
    ou na pasta do script Python (em desenvolvimento).
    """
    base_path = get_base_path()
    return os.path.join(base_path, relative_path) if relative_path else base_path


DEFAULT_EN_TRANSLATIONS: Dict[str, str] = {
    "app_title": "PyDiagram - UML & Diagram Modeler",
    "menu_file": "&File",
    "action_new": "&New Diagram",
    "action_open": "&Open...",
    "action_save": "&Save",
    "action_export": "&Export as Image...",
    "action_exit": "E&xit",
    "menu_edit": "&Edit",
    "action_undo": "&Undo",
    "action_redo": "&Redo",
    "action_delete": "&Delete Selected",
    "menu_diagram": "&Diagram",
    "menu_connections": "UML Connections",
    "action_add_node": "Add &Node",
    "action_clear": "&Clear All",
    "menu_language": "&Language",
    "lang_pt_br": "Português (pt-BR)",
    "lang_en_us": "English (en-US)",
    "menu_help": "&Help",
    "action_about": "&About PyDiagram",
    "toolbar_tools": "Tools",
    "toolbar_add_node": "New Node",
    "toolbar_connect": "Connect",
    "toolbar_delete": "Delete",
    "explorer_title": "Model Explorer",
    "properties_title": "Properties",
    "status_ready": "Ready",
    "status_node_added": "Node added to diagram.",
    "status_nodes_connected": "Nodes connected successfully.",
    "status_select_two_nodes": "Select exactly 2 nodes to connect.",
    "status_deleted": "Item(s) deleted.",
    "export_dialog_title": "Export as Image",
    "export_filter": "PNG Images (*.png);;JPEG Images (*.jpg *.jpeg)",
    "status_export_success": "Diagram successfully exported: {path}",
    "status_export_empty": "Diagram is empty. Nothing to export.",
    "export_error_title": "Export Error",
    "export_error_msg": "Could not save the image file.",
    "about_title": "About PyDiagram",
    "about_text": "PyDiagram - Open-Source Diagram Modeler inspired by StarUML.\nBuilt with Python e PyQt6.",
    "action_new_class": "New Class",
    "action_toggle_sidebar": "Show Explorer / Properties",
    "action_connection_mode": "Connect Classes",
    "status_connection_mode_active": "Connection Mode active: Click and drag from one class to another.",
    "status_connection_mode_inactive": "Normal selection mode active.",
    "minimap_title": "Minimap",
    "action_save_project": "&Save Project...",
    "action_open_project": "&Open Project...",
}

DEFAULT_PT_BR_TRANSLATIONS: Dict[str, str] = {
    "app_title": "PyDiagram - Modelador UML & Diagramas",
    "menu_file": "&Arquivo",
    "action_new": "&Novo Diagrama",
    "action_open": "&Abrir...",
    "action_save": "&Salvar",
    "action_export": "&Exportar como Imagem...",
    "action_exit": "&Sair",
    "menu_edit": "&Editar",
    "action_undo": "&Desfazer",
    "action_redo": "&Refazer",
    "action_delete": "&Excluir Selecionado",
    "menu_diagram": "&Diagrama",
    "menu_connections": "Conexões UML",
    "action_add_node": "Adicionar &Nó",
    "action_clear": "&Limpar Tudo",
    "menu_language": "&Idioma",
    "menu_help": "Aj&uda",
    "action_about": "&Sobre o PyDiagram",
    "toolbar_tools": "Ferramentas",
    "toolbar_add_node": "Novo Nó",
    "toolbar_connect": "Conectar",
    "toolbar_delete": "Excluir",
    "explorer_title": "Explorador de Modelos",
    "properties_title": "Propriedades",
    "status_ready": "Pronto",
    "status_node_added": "Nó adicionado ao diagrama.",
    "status_nodes_connected": "Nós conectados com sucesso.",
    "status_select_two_nodes": "Selecione exatamente 2 nós para conectar.",
    "status_deleted": "Item(ns) excluído(s).",
    "export_dialog_title": "Exportar como Imagem",
    "export_filter": "Imagens PNG (*.png);;Imagens JPEG (*.jpg *.jpeg)",
    "status_export_success": "Diagrama exportado com sucesso: {path}",
    "status_export_empty": "O diagrama está vazio. Nenhum item para exportar.",
    "export_error_title": "Erro ao Exportar",
    "export_error_msg": "Não foi possível salvar o arquivo de imagem.",
    "about_title": "Sobre o PyDiagram",
    "about_text": "PyDiagram - Modelador Open-Source inspirado no StarUML.\nConstruído com Python e PyQt6.",
    "action_new_class": "Nova Classe",
    "action_toggle_sidebar": "Exibir Explorador / Propriedades",
    "action_connection_mode": "Conectar Classes",
    "status_connection_mode_active": "Modo de Conexão ativo: Clique em uma classe e arraste até outra.",
    "status_connection_mode_inactive": "Modo normal de seleção ativo.",
    "minimap_title": "Minimapa",
    "action_save_project": "&Salvar Projeto...",
    "action_open_project": "&Abrir Projeto...",
}


def ensure_locales_directory(locales_dir: Optional[str | Path] = None) -> Path:
    """
    Garante que a pasta `locales` existe ao lado do executável (ou script .py)
    usando os.path.join(base_path, 'locales') e cria `_template.json` dentro dela.
    """
    if locales_dir is not None:
        locales_path = str(locales_dir)
    else:
        base_path = (
            os.path.dirname(sys.executable)
            if getattr(sys, "frozen", False)
            else os.path.abspath(os.path.dirname(__file__))
        )
        locales_path = os.path.join(base_path, "locales")

    target_path = Path(locales_path)
    if not os.path.exists(locales_path):
        try:
            os.makedirs(locales_path, exist_ok=True)
        except OSError as exc:
            print(f"[i18n] Aviso ao criar diretório '{locales_path}': {exc}", file=sys.stderr)
            return target_path

    template_file = os.path.join(locales_path, "_template.json")
    json_files = [
        f for f in os.listdir(locales_path) if f.lower().endswith(".json")
    ] if os.path.exists(locales_path) else []

    if not os.path.exists(template_file):
        template_payload = {
            "_enabled": False,
            "_lang_name": "Template Language (xx-XX)",
            "translations": dict(DEFAULT_EN_TRANSLATIONS),
        }
        try:
            with open(template_file, "w", encoding="utf-8") as f:
                json.dump(template_payload, f, indent=2, ensure_ascii=False)
        except OSError as exc:
            print(f"[i18n] Aviso ao criar '_template.json' em '{locales_path}': {exc}", file=sys.stderr)

    # Se não houver outros ficheiros de idioma ativos além do _template.json, cria os idiomas padrão
    non_template_files = [f for f in json_files if f != "_template.json"]
    if not non_template_files:
        en_payload = {
            "_enabled": True,
            "_lang_name": "English (en-US)",
            "translations": dict(DEFAULT_EN_TRANSLATIONS),
        }
        pt_payload = {
            "_enabled": True,
            "_lang_name": "Português (pt-BR)",
            "translations": dict(DEFAULT_PT_BR_TRANSLATIONS),
        }
        try:
            en_path = os.path.join(locales_path, "en-US.json")
            if not os.path.exists(en_path):
                with open(en_path, "w", encoding="utf-8") as f:
                    json.dump(en_payload, f, indent=2, ensure_ascii=False)
            pt_path = os.path.join(locales_path, "pt-BR.json")
            if not os.path.exists(pt_path):
                with open(pt_path, "w", encoding="utf-8") as f:
                    json.dump(pt_payload, f, indent=2, ensure_ascii=False)
        except OSError as exc:
            print(f"[i18n] Aviso ao criar ficheiros padrão em '{locales_path}': {exc}", file=sys.stderr)

    return target_path


def load_languages(locales_dir: Optional[str | Path] = None) -> Dict[str, Dict[str, Any]]:
    """
    Itera por todos os ficheiros .json dentro da pasta `locales` (em os.path.join(base_path, 'locales'))
    de forma segura (try-except). Apenas carrega idiomas onde `"_enabled"` existe e é `True`.
    Retorna dicionário: {lang_code: {"_lang_name": str, "translations": Dict[str, str]}}.
    """
    target_path = ensure_locales_directory(locales_dir)
    locales_path = str(target_path)
    loaded: Dict[str, Dict[str, Any]] = {}

    if not os.path.exists(locales_path):
        return loaded

    for filename in sorted(os.listdir(locales_path)):
        if not filename.lower().endswith(".json"):
            continue
        lang_code = os.path.splitext(filename)[0]
        resolved_file = os.path.join(locales_path, filename)
        try:
            if os.path.getsize(resolved_file) == 0:
                print(f"[i18n] Aviso: ficheiro de idioma vazio ignorado: '{resolved_file}'", file=sys.stderr)
                continue

            with open(resolved_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            if not isinstance(data, dict):
                print(f"[i18n] Aviso: formato inválido em '{resolved_file}' (ignorado).", file=sys.stderr)
                continue

            if data.get("_enabled") is not True:
                print(
                    f"[i18n] Aviso: idioma '{lang_code}' ignorado ('_enabled' ausente ou false).",
                    file=sys.stderr,
                )
                continue

            lang_name = str(data.get("_lang_name") or lang_code).strip()
            translations = data.get("translations")
            if not isinstance(translations, dict):
                # Fallback caso as chaves estejam no nível raiz junto com _enabled
                translations = {
                    str(k): str(v)
                    for k, v in data.items()
                    if not str(k).startswith("_") and isinstance(v, str)
                }

            loaded[lang_code] = {
                "_enabled": True,
                "_lang_name": lang_name,
                "translations": {str(k): str(v) for k, v in translations.items()},
            }
        except Exception as exc:
            print(
                f"[i18n] Aviso: falha ao ler ficheiro de idioma '{resolved_file}' (ignorado): {exc}",
                file=sys.stderr,
            )

    return loaded


class I18nManager:
    """Gerencia traduções e troca de idioma dinamicamente a partir da pasta locales."""

    def __init__(
        self, locales_dir: Optional[Path | str] = None, default_lang: str = "pt-BR"
    ) -> None:
        if locales_dir is not None:
            self.locales_dir = Path(locales_dir)
        else:
            base_path = (
                os.path.dirname(sys.executable)
                if getattr(sys, "frozen", False)
                else os.path.abspath(os.path.dirname(__file__))
            )
            self.locales_dir = Path(os.path.join(base_path, "locales"))
        self.languages: Dict[str, Dict[str, Any]] = {}
        self.translations: Dict[str, Dict[str, str]] = {}
        self.language_names: Dict[str, str] = {}
        self.current_lang = default_lang
        self.load_languages()

    def load_languages(self) -> Dict[str, Dict[str, Any]]:
        """Carrega apenas os idiomas habilitados (_enabled: true) da pasta locales."""
        self.languages = load_languages(self.locales_dir)
        self.translations = {
            code: info["translations"] for code, info in self.languages.items()
        }
        self.language_names = {
            code: info["_lang_name"] for code, info in self.languages.items()
        }
        if self.current_lang not in self.translations and self.translations:
            self.current_lang = next(iter(self.translations.keys()))
        return self.languages

    load_locales = load_languages

    def t(self, key: str, fallback: str = "") -> str:
        """Retorna o texto traduzido para a chave informada."""
        lang_dict = self.translations.get(self.current_lang, {})
        return lang_dict.get(key, fallback or key)

    def set_language(self, lang_code: str) -> bool:
        """Altera o idioma ativo."""
        if lang_code in self.translations:
            self.current_lang = lang_code
            return True
        return False


# ==============================================================================
# 2. Janela Principal (MainWindow)
# ==============================================================================
class MainWindow(QMainWindow):
    """Janela principal do aplicativo de modelagem e diagramação UML."""

    def __init__(self) -> None:
        super().__init__()
        self.resize(1100, 750)

        # Internacionalização usando get_resource_path (compatível com PyInstaller)
        locales_dir = Path(get_resource_path("locales"))
        self.i18n = I18nManager(locales_dir, default_lang="pt-BR")

        # Cena e Canvas com otimizações ativas
        self.scene = DiagramScene(self)
        self.view = DiagramView(self.scene, self)

        # Estados internos e controle de concorrência de propriedades
        self._is_populating_properties: bool = False
        self._is_applying_properties: bool = False
        self.current_property_item: Optional[Any] = None
        self.current_prop_color: QColor = QColor(51, 65, 85)
        self.current_connection_type: str = "Generalization"
        self.scene.connection_type = self.current_connection_type
        self.node_counter: int = 1

        # Construção da Interface
        self.setup_ui_layout()
        self.create_actions()
        self.create_menus()
        self.create_toolbar()
        self.create_statusbar()

        # Conexão de seleção do canvas
        self.scene.selectionChanged.connect(self.on_scene_selection_changed)

        # Inicialização limpa da árvore e painel (sem nós pré-criados)
        self.update_tree()
        self.populate_properties(None)
        self.retranslate_ui()

    def setup_ui_layout(self) -> None:
        """Configura a disposição com Splitters, QDockWidget e painel de propriedades."""
        self.sidebar_splitter = QSplitter(Qt.Orientation.Vertical)

        # 1. Árvore do Explorador
        self.tree_widget = QTreeWidget(self.sidebar_splitter)
        self.tree_widget.setHeaderLabels([self.i18n.t("explorer_title", "Explorador de Modelos")])
        self.tree_widget.setAlternatingRowColors(False)
        self.tree_widget.setStyleSheet(
            """
            QTreeWidget {
                background-color: #2b2b2b;
                color: #e0e0e0;
                border: none;
            }
            QTreeWidget::item {
                padding: 4px;
            }
            QTreeWidget::item:selected {
                background-color: #444444;
                color: #ffffff;
            }
            QTreeWidget::item:hover {
                background-color: #383838;
            }
            QTreeWidget:focus {
                outline: none;
            }
            """
        )
        self.tree_widget.itemClicked.connect(self.on_tree_item_clicked)

        # 2. Painel de Propriedades
        self.prop_group = QGroupBox("Properties", self.sidebar_splitter)
        self.prop_layout = QFormLayout(self.prop_group)
        self.prop_layout.setContentsMargins(10, 14, 10, 10)
        self.prop_layout.setVerticalSpacing(8)

        self.prop_name_edit = QLineEdit(self.prop_group)
        self.prop_name_edit.setPlaceholderText("Nome...")

        self.prop_visibility_combo = QComboBox(self.prop_group)
        self.prop_visibility_combo.addItems([
            "public (+)",
            "private (-)",
            "protected (#)",
            "none",
        ])

        self.prop_abstract_check = QCheckBox(self.prop_group)

        self.prop_font_combo = QFontComboBox(self.prop_group)
        self.prop_size_spin = QSpinBox(self.prop_group)
        self.prop_size_spin.setRange(8, 72)
        self.prop_size_spin.setValue(9)

        self.prop_color_btn = QPushButton("Mudar Cor", self.prop_group)
        self._update_color_btn_style(self.current_prop_color)

        self.connection_type_combo = QComboBox(self.prop_group)
        self.connection_type_combo.addItems([
            "Association",
            "Directed Association",
            "Aggregation",
            "Composition",
            "Dependency",
            "Generalization",
            "Realization",
            "Interface Realization",
        ])
        self.connection_type_combo.setCurrentText(self.current_connection_type)

        self.prop_layout.addRow("name", self.prop_name_edit)
        self.prop_layout.addRow("visibility", self.prop_visibility_combo)
        self.prop_layout.addRow("isAbstract", self.prop_abstract_check)
        self.prop_layout.addRow("font", self.prop_font_combo)
        self.prop_layout.addRow("size", self.prop_size_spin)
        self.prop_layout.addRow("color", self.prop_color_btn)
        self.prop_layout.addRow("connectionType", self.connection_type_combo)

        # Conecta sinais do formulário apenas uma vez
        self.prop_name_edit.textEdited.connect(self.apply_properties)
        self.prop_visibility_combo.currentIndexChanged.connect(self.apply_properties)
        self.prop_abstract_check.stateChanged.connect(self.apply_properties)
        self.prop_font_combo.currentFontChanged.connect(self.apply_properties)
        self.prop_size_spin.valueChanged.connect(self.apply_properties)
        self.prop_color_btn.clicked.connect(self.choose_property_color)
        self.connection_type_combo.currentTextChanged.connect(self.on_connection_type_changed)

        # 3. Minimapa com atualização debounced (evita lag em mudanças rápidas)
        self.minimap_group = QGroupBox(self.i18n.t("minimap_title", "Minimapa"), self.sidebar_splitter)
        minimap_layout = QVBoxLayout(self.minimap_group)
        minimap_layout.setContentsMargins(6, 10, 6, 6)

        self.minimap_view = MinimapView(self.scene, main_view=self.view, parent=self.minimap_group)
        self.minimap_view.setMinimumHeight(120)
        self.view.minimap_view = self.minimap_view
        minimap_layout.addWidget(self.minimap_view)

        # Timer debounce para o minimapa (80ms)
        self._minimap_timer = QTimer(self)
        self._minimap_timer.setSingleShot(True)
        self._minimap_timer.setInterval(80)
        self._minimap_timer.timeout.connect(self.minimap_view.update_minimap)
        self.scene.changed.connect(lambda _: self._minimap_timer.start())

        self.sidebar_splitter.addWidget(self.tree_widget)
        self.sidebar_splitter.addWidget(self.prop_group)
        self.sidebar_splitter.addWidget(self.minimap_group)
        self.sidebar_splitter.setSizes([320, 260, 150])

        # Dock lateral
        self.sidebar_dock = QDockWidget(self.i18n.t("explorer_title", "Explorador de Modelos"), self)
        self.sidebar_dock.setObjectName("SidebarDock")
        self.sidebar_dock.setWidget(self.sidebar_splitter)
        self.sidebar_dock.setAllowedAreas(
            Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea
        )
        self.sidebar_dock.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable
            | QDockWidget.DockWidgetFeature.DockWidgetFloatable
        )
        self.sidebar_dock.setMinimumWidth(260)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.sidebar_dock)
        self.resizeDocks([self.sidebar_dock], [280], Qt.Orientation.Horizontal)

        # View central
        self.setCentralWidget(self.view)

    def choose_property_color(self) -> None:
        """Abre diálogo para seleção da cor de texto do elemento atual."""
        if self._is_populating_properties or self.current_property_item is None:
            return
        initial_color = self.current_prop_color
        chosen = QColorDialog.getColor(initial_color, self, "Escolher Cor do Texto")
        if chosen.isValid():
            self.current_prop_color = chosen
            self._update_color_btn_style(chosen)
            self.apply_properties()

    def _update_color_btn_style(self, color: QColor) -> None:
        """Atualiza a cor de fundo e contraste do botão de cor."""
        hex_color = color.name()
        lum = color.red() * 0.299 + color.green() * 0.587 + color.blue() * 0.114
        text_color = "#ffffff" if lum < 128 else "#0f172a"
        self.prop_color_btn.setStyleSheet(
            f"background-color: {hex_color}; color: {text_color}; font-weight: bold; padding: 4px; border-radius: 4px;"
        )

    def update_connection_button_text(self) -> None:
        """Atualiza o texto do botão principal para exibir a conexão selecionada."""
        prefix = self.i18n.t("toolbar_connect", "Conectar")
        label = f"{prefix}: {self.current_connection_type}"
        if hasattr(self, "connection_tool_button") and self.connection_tool_button:
            self.connection_tool_button.setText(label)
        if hasattr(self, "action_connection_mode") and self.action_connection_mode:
            self.action_connection_mode.setText(label)

    def on_connection_action_triggered(self, action_name: str) -> None:
        """
        Ativa o modo de conexão e define automaticamente o connection_type da cena
        com base na ação escolhida no menu 'Conexões UML'.
        """
        self.current_connection_type = action_name
        self.scene.connection_type = action_name

        if hasattr(self, "connection_type_combo"):
            self.connection_type_combo.blockSignals(True)
            idx = self.connection_type_combo.findText(action_name)
            if idx >= 0:
                self.connection_type_combo.setCurrentIndex(idx)
            self.connection_type_combo.blockSignals(False)

        if hasattr(self, "connection_actions") and action_name in self.connection_actions:
            self.connection_actions[action_name].setChecked(True)

        self.update_connection_button_text()

        if isinstance(self.current_property_item, DiagramConnectionItem):
            self.current_property_item.set_connection_type(action_name)

        self.scene.set_connection_mode(True)
        if hasattr(self, "action_connection_mode"):
            self.action_connection_mode.setChecked(True)
        if hasattr(self, "connection_tool_button"):
            self.connection_tool_button.setChecked(True)

        if hasattr(self, "statusbar") and self.statusbar:
            self.statusbar.showMessage(
                f"Modo de Conexão ({action_name}) ativo: Clique em uma classe e arraste até outra.",
                5000,
            )

    def on_connection_type_changed(self, text: str) -> None:
        """Sincroniza o tipo de conexão selecionado com a cena, menu e conexões ativas."""
        self.current_connection_type = text
        self.scene.connection_type = text
        if hasattr(self, "connection_actions") and text in self.connection_actions:
            self.connection_actions[text].setChecked(True)
        self.update_connection_button_text()

        if getattr(self, "_is_populating_properties", False):
            return
        if isinstance(self.current_property_item, DiagramConnectionItem):
            self.current_property_item.set_connection_type(text)

    def populate_properties(self, selected_item: Optional[Any]) -> None:
        """Preenche o formulário de propriedades com base no item ativo."""
        self._is_populating_properties = True
        try:
            self.current_property_item = selected_item
            if hasattr(self, "connection_type_combo"):
                self.connection_type_combo.setEnabled(True)

            if selected_item is None or isinstance(selected_item, DiagramConnectionItem):
                self.prop_name_edit.setEnabled(False)
                self.prop_visibility_combo.setEnabled(False)
                self.prop_abstract_check.setEnabled(False)
                self.prop_font_combo.setEnabled(False)
                self.prop_size_spin.setEnabled(False)
                self.prop_color_btn.setEnabled(False)
                self.prop_name_edit.clear()
                self.prop_visibility_combo.setCurrentIndex(3)
                self.prop_abstract_check.setChecked(False)
                if isinstance(selected_item, DiagramConnectionItem) and hasattr(self, "connection_type_combo"):
                    idx = self.connection_type_combo.findText(selected_item.connection_type)
                    if idx >= 0:
                        self.connection_type_combo.setCurrentIndex(idx)
                return

            self.prop_name_edit.setEnabled(True)
            self.prop_visibility_combo.setEnabled(True)
            self.prop_abstract_check.setEnabled(True)
            self.prop_font_combo.setEnabled(True)
            self.prop_size_spin.setEnabled(True)
            self.prop_color_btn.setEnabled(True)

            if isinstance(selected_item, DiagramNodeItem):
                clean_name = selected_item.title
                if clean_name and clean_name[0] in ("+", "-", "#", "~"):
                    clean_name = clean_name[1:].lstrip()
                self.prop_name_edit.setText(clean_name)
                self.prop_visibility_combo.setCurrentIndex(3)
                self.prop_abstract_check.setChecked(selected_item.is_abstract)

                t_font = selected_item.title_item.font()
                self.prop_font_combo.setCurrentFont(t_font)
                self.prop_size_spin.setValue(t_font.pointSize() or 10)
                t_color = selected_item.title_item.defaultTextColor()
                self.current_prop_color = t_color
                self._update_color_btn_style(t_color)

            elif isinstance(selected_item, EditableTextItem):
                raw_text = selected_item.toPlainText().strip()
                if raw_text.startswith("+"):
                    self.prop_visibility_combo.setCurrentIndex(0)
                    raw_text = raw_text[1:].lstrip()
                elif raw_text.startswith("-"):
                    self.prop_visibility_combo.setCurrentIndex(1)
                    raw_text = raw_text[1:].lstrip()
                elif raw_text.startswith("#"):
                    self.prop_visibility_combo.setCurrentIndex(2)
                    raw_text = raw_text[1:].lstrip()
                else:
                    self.prop_visibility_combo.setCurrentIndex(3)

                self.prop_name_edit.setText(raw_text)
                self.prop_abstract_check.setChecked(selected_item.font().italic())

                m_font = selected_item.font()
                self.prop_font_combo.setCurrentFont(m_font)
                self.prop_size_spin.setValue(m_font.pointSize() or 9)
                m_color = selected_item.defaultTextColor()
                self.current_prop_color = m_color
                self._update_color_btn_style(m_color)
        finally:
            self._is_populating_properties = False

    def select_in_tree(self, target_obj: Any) -> None:
        """Sincroniza a seleção visual na árvore com o objeto fornecido."""
        if target_obj is None:
            self.tree_widget.clearSelection()
            return

        def _search(item: QTreeWidgetItem) -> bool:
            if item.data(0, Qt.ItemDataRole.UserRole) == target_obj:
                self.tree_widget.blockSignals(True)
                self.tree_widget.setCurrentItem(item)
                item.setSelected(True)
                self.tree_widget.blockSignals(False)
                return True
            for i in range(item.childCount()):
                if _search(item.child(i)):
                    return True
            return False

        for i in range(self.tree_widget.topLevelItemCount()):
            if _search(self.tree_widget.topLevelItem(i)):
                return

    def apply_properties(self) -> None:
        """Aplica as edições do painel de propriedades ao elemento ativo."""
        if getattr(self, "_is_populating_properties", False):
            return
        if getattr(self, "_is_applying_properties", False):
            return
        if self.current_property_item is None:
            return

        self._is_applying_properties = True
        try:
            name_val = self.prop_name_edit.text()
            vis_index = self.prop_visibility_combo.currentIndex()
            vis_map = {0: "+", 1: "-", 2: "#", 3: ""}
            symbol = vis_map.get(vis_index, "")
            is_abstract = self.prop_abstract_check.isChecked()

            chosen_font = self.prop_font_combo.currentFont()
            chosen_size = self.prop_size_spin.value()
            chosen_color = self.current_prop_color

            node_to_update: Optional[DiagramNodeItem] = None

            if isinstance(self.current_property_item, DiagramNodeItem):
                node = self.current_property_item
                node_to_update = node

                if name_val.strip():
                    formatted = EditableTextItem.format_uml_title(name_val)
                    node.title_item.setPlainText(formatted)

                node.is_abstract = is_abstract
                font = QFont(chosen_font.family(), chosen_size)
                font.setBold(True)
                font.setItalic(is_abstract)
                node.title_item.setFont(font)
                node.title_item.setDefaultTextColor(chosen_color)

            elif isinstance(self.current_property_item, EditableTextItem):
                member = self.current_property_item
                node_to_update = member.node_parent

                clean_text = name_val.strip()
                if clean_text and clean_text[0] in ("+", "-", "#", "~"):
                    clean_text = clean_text[1:].lstrip()

                if symbol:
                    new_text = f"{symbol} {clean_text}" if clean_text else symbol
                else:
                    new_text = clean_text

                if member.item_type == "method" and new_text:
                    if not new_text.endswith(")") and "):" not in new_text:
                        new_text = f"{new_text}()"

                member.setPlainText(new_text)

                font = QFont(chosen_font.family(), chosen_size)
                font.setItalic(is_abstract)
                member.setFont(font)
                member.setDefaultTextColor(chosen_color)

            if node_to_update:
                node_to_update.update_layout()

            self.update_tree_item_label(self.current_property_item)
        finally:
            self._is_applying_properties = False

    def on_scene_selection_changed(self) -> None:
        """Atualiza painel de propriedades quando a seleção do canvas muda."""
        selected_items = self.scene.selectedItems()
        selected_nodes = [
            it for it in selected_items if isinstance(it, DiagramNodeItem)
        ]
        selected_conns = [
            it for it in selected_items if isinstance(it, DiagramConnectionItem)
        ]
        if selected_nodes:
            node = selected_nodes[0]
            self.populate_properties(node)
            self.select_in_tree(node)
        elif selected_conns:
            self.populate_properties(selected_conns[0])
            self.select_in_tree(None)
        else:
            if not isinstance(self.current_property_item, EditableTextItem):
                self.populate_properties(None)

    def on_tree_item_clicked(self, item: QTreeWidgetItem, column: int) -> None:
        """Trata seleção por clique no item da árvore."""
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if isinstance(data, DiagramNodeItem):
            self.scene.blockSignals(True)
            self.scene.clearSelection()
            data.setSelected(True)
            self.scene.blockSignals(False)
            self.populate_properties(data)
        elif isinstance(data, EditableTextItem):
            if data.node_parent:
                self.scene.blockSignals(True)
                self.scene.clearSelection()
                data.node_parent.setSelected(True)
                self.scene.blockSignals(False)
            self.populate_properties(data)
        else:
            self.populate_properties(None)

    def update_model_tree(self) -> None:
        """Reconstrói a árvore do explorador com todas as classes e seus membros."""
        self.tree_widget.blockSignals(True)
        try:
            self.tree_widget.clear()
            nodes = [it for it in self.scene.items() if isinstance(it, DiagramNodeItem)]
            nodes.sort(key=lambda n: n.pos().y())

            for node in nodes:
                class_item = QTreeWidgetItem([node.title])
                class_item.setData(0, Qt.ItemDataRole.UserRole, node)
                class_item.setExpanded(True)

                if getattr(node, "is_abstract", False):
                    font = class_item.font(0)
                    font.setItalic(True)
                    class_item.setFont(0, font)

                for attr in node.attribute_items:
                    attr_leaf = QTreeWidgetItem([attr.toPlainText()])
                    attr_leaf.setData(0, Qt.ItemDataRole.UserRole, attr)
                    if hasattr(attr, "font") and attr.font().italic():
                        font = attr_leaf.font(0)
                        font.setItalic(True)
                        attr_leaf.setFont(0, font)
                    class_item.addChild(attr_leaf)

                for method in node.method_items:
                    method_leaf = QTreeWidgetItem([method.toPlainText()])
                    method_leaf.setData(0, Qt.ItemDataRole.UserRole, method)
                    if hasattr(method, "font") and method.font().italic():
                        font = method_leaf.font(0)
                        font.setItalic(True)
                        method_leaf.setFont(0, font)
                    class_item.addChild(method_leaf)

                self.tree_widget.addTopLevelItem(class_item)

            if self.current_property_item:
                self.select_in_tree(self.current_property_item)
        finally:
            self.tree_widget.blockSignals(False)

    update_tree = update_model_tree

    def _update_tree_item_italic(self, tree_item: QTreeWidgetItem, item_obj: Any) -> None:
        """Atualiza estilo itálico no item da árvore."""
        is_abstract = False
        if isinstance(item_obj, DiagramNodeItem):
            is_abstract = getattr(item_obj, "is_abstract", False)
        elif isinstance(item_obj, EditableTextItem):
            is_abstract = item_obj.font().italic()

        font = tree_item.font(0)
        font.setItalic(is_abstract)
        tree_item.setFont(0, font)

    def update_tree_item_label(self, item_obj: Any) -> None:
        """Atualiza pontualmente o texto e estilo do item na árvore sem rebuild global."""
        if not item_obj:
            return

        current_tree_item = self.tree_widget.currentItem()
        if (
            current_tree_item
            and current_tree_item.data(0, Qt.ItemDataRole.UserRole) == item_obj
        ):
            if isinstance(item_obj, DiagramNodeItem):
                current_tree_item.setText(0, item_obj.title)
            elif isinstance(item_obj, EditableTextItem):
                current_tree_item.setText(0, item_obj.toPlainText())
            self._update_tree_item_italic(current_tree_item, item_obj)
            return

        for i in range(self.tree_widget.topLevelItemCount()):
            top = self.tree_widget.topLevelItem(i)
            if top.data(0, Qt.ItemDataRole.UserRole) == item_obj:
                top.setText(0, item_obj.title)
                self._update_tree_item_italic(top, item_obj)
                return
            for j in range(top.childCount()):
                child = top.child(j)
                if child.data(0, Qt.ItemDataRole.UserRole) == item_obj:
                    child.setText(0, item_obj.toPlainText())
                    self._update_tree_item_italic(child, item_obj)
                    return

    def create_actions(self) -> None:
        """Cria e conecta as ações da barra de menus e ferramentas."""
        self.action_new = QAction(self)
        self.action_new.setShortcut("Ctrl+N")
        self.action_new.triggered.connect(self.on_clear_diagram)

        self.action_open_project = QAction(self)
        self.action_open_project.setShortcut("Ctrl+O")
        self.action_open_project.triggered.connect(self.load_project)

        self.action_save_project = QAction(self)
        self.action_save_project.setShortcut("Ctrl+S")
        self.action_save_project.triggered.connect(self.save_project)

        self.action_export = QAction(self)
        self.action_export.setShortcut("Ctrl+E")
        self.action_export.triggered.connect(self.export_to_image)

        self.action_exit = QAction(self)
        self.action_exit.setShortcut("Ctrl+Q")
        self.action_exit.triggered.connect(self.close)

        self.action_delete = QAction(self)
        self.action_delete.setShortcut("Delete")
        self.action_delete.triggered.connect(self.on_delete_selected)

        self.action_add_node = QAction(self)
        self.action_add_node.setShortcut("Ctrl+T")
        self.action_add_node.triggered.connect(self.on_add_node)

        self.action_connection_mode = QAction(self)
        self.action_connection_mode.setCheckable(True)
        self.action_connection_mode.setChecked(False)
        self.action_connection_mode.toggled.connect(self.on_connection_mode_toggled)
        self.scene.connection_mode_changed.connect(self._on_scene_connection_mode_changed)

        # Menu dedicado de Conexões UML e respectivas QActions
        self.connection_menu = QMenu("Conexões UML", self)
        self.connection_action_group = QActionGroup(self)
        self.connection_action_group.setExclusive(True)
        self.connection_actions: Dict[str, QAction] = {}

        uml_connection_types = [
            "Association",
            "Directed Association",
            "Aggregation",
            "Composition",
            "Dependency",
            "Generalization",
            "Realization",
            "Interface Realization",
        ]
        for conn_type in uml_connection_types:
            act = QAction(conn_type, self)
            act.setCheckable(True)
            if conn_type == self.current_connection_type:
                act.setChecked(True)
            act.triggered.connect(
                lambda checked=False, ct=conn_type: self.on_connection_action_triggered(ct)
            )
            self.connection_action_group.addAction(act)
            self.connection_menu.addAction(act)
            self.connection_actions[conn_type] = act

        self.lang_action_group = QActionGroup(self)
        self.lang_action_group.setExclusive(True)
        self.language_actions: Dict[str, QAction] = {}

        self.action_about = QAction(self)
        self.action_about.triggered.connect(self.on_show_about)

    def _on_scene_connection_mode_changed(self, enabled: bool) -> None:
        """Sincroniza o estado visual dos controles quando o modo de conexão muda na cena."""
        if hasattr(self, "action_connection_mode"):
            self.action_connection_mode.blockSignals(True)
            self.action_connection_mode.setChecked(enabled)
            self.action_connection_mode.blockSignals(False)
        if hasattr(self, "connection_tool_button") and self.connection_tool_button:
            self.connection_tool_button.setChecked(enabled)

    def on_connection_mode_toggled(self, checked: bool) -> None:
        self.scene.connection_type = self.current_connection_type
        self.scene.connection_mode = checked
        if hasattr(self, "connection_tool_button") and self.connection_tool_button:
            self.connection_tool_button.setChecked(checked)
        if checked:
            self.statusbar.showMessage(
                f"Modo de Conexão ({self.current_connection_type}) ativo: Clique em uma classe e arraste até outra.",
                5000,
            )
        else:
            self.statusbar.showMessage(
                self.i18n.t("status_connection_mode_inactive", "Modo normal de seleção ativo."),
                3000,
            )

    def create_menus(self) -> None:
        """Cria e organiza os menus superiores."""
        menubar = self.menuBar()

        self.menu_file = menubar.addMenu("")
        self.menu_file.addAction(self.action_new)
        self.menu_file.addAction(self.action_open_project)
        self.menu_file.addAction(self.action_save_project)
        self.menu_file.addSeparator()
        self.menu_file.addAction(self.action_export)
        self.menu_file.addSeparator()
        self.menu_file.addAction(self.action_exit)

        self.menu_edit = menubar.addMenu("")
        self.menu_edit.addAction(self.action_delete)

        self.menu_diagram = menubar.addMenu("")
        self.menu_diagram.addAction(self.action_add_node)
        self.menu_diagram.addMenu(self.connection_menu)
        if hasattr(self, "sidebar_dock"):
            self.menu_diagram.addSeparator()
            self.menu_diagram.addAction(self.sidebar_dock.toggleViewAction())

        # Menu dedicado "Conexões UML" na barra de menus principal (MenuBar)
        self.menu_connections = self.connection_menu
        menubar.addMenu(self.connection_menu)

        self.menu_language = menubar.addMenu("")
        self.populate_language_menu()

        self.menu_help = menubar.addMenu("")
        self.menu_help.addAction(self.action_about)

    def load_languages(self) -> Dict[str, Dict[str, Any]]:
        """Recarrega os idiomas válidos da pasta locales e reconstrói o menu Idioma."""
        langs = self.i18n.load_languages()
        if hasattr(self, "menu_language") and self.menu_language is not None:
            self.populate_language_menu()
        return langs

    def populate_language_menu(self) -> None:
        """
        Limpa o menu 'Idioma' e recria dinamicamente as opções (QAction)
        lendo as chaves '_lang_name' dos ficheiros JSON validados (_enabled: true).
        """
        self.menu_language.clear()
        self.lang_action_group = QActionGroup(self)
        self.lang_action_group.setExclusive(True)
        self.language_actions.clear()

        for lang_code, lang_info in self.i18n.languages.items():
            lang_name = str(lang_info.get("_lang_name") or lang_code)
            action = QAction(lang_name, self)
            action.setCheckable(True)
            action.setData(lang_code)
            if lang_code == self.i18n.current_lang:
                action.setChecked(True)
            action.triggered.connect(
                lambda checked=False, lc=lang_code: self.switch_language(lc)
            )
            self.lang_action_group.addAction(action)
            self.menu_language.addAction(action)
            self.language_actions[lang_code] = action

        if "pt-BR" in self.language_actions:
            self.action_lang_pt = self.language_actions["pt-BR"]
        if "en-US" in self.language_actions:
            self.action_lang_en = self.language_actions["en-US"]

    def create_toolbar(self) -> None:
        """Cria a barra de ferramentas principal com QToolButton suspenso para Conexões UML."""
        self.toolbar = QToolBar(self)
        self.toolbar.setMovable(False)
        self.addToolBar(self.toolbar)

        self.toolbar.addAction(self.action_open_project)
        self.toolbar.addAction(self.action_save_project)
        self.toolbar.addSeparator()
        self.toolbar.addAction(self.action_add_node)

        self.connection_tool_button = QToolButton(self)
        self.connection_tool_button.setMenu(self.connection_menu)
        self.connection_tool_button.setPopupMode(
            QToolButton.ToolButtonPopupMode.InstantPopup
        )
        self.connection_tool_button.setCheckable(True)
        self.connection_tool_button.setText(f"Conectar: {self.current_connection_type}")
        self.toolbar.addWidget(self.connection_tool_button)

        self.toolbar.addSeparator()
        self.toolbar.addAction(self.action_export)
        self.toolbar.addAction(self.action_delete)

    def create_statusbar(self) -> None:
        self.statusbar = QStatusBar(self)
        self.setStatusBar(self.statusbar)

    def switch_language(self, lang_code: str) -> None:
        if self.i18n.set_language(lang_code):
            if hasattr(self, "language_actions") and lang_code in self.language_actions:
                self.language_actions[lang_code].setChecked(True)
            self.retranslate_ui()

    def retranslate_ui(self) -> None:
        """Aplica os textos traduzidos à janela e seus componentes em tempo real."""
        self.setWindowTitle(self.i18n.t("app_title", "PyDiagram"))

        self.menu_file.setTitle(self.i18n.t("menu_file", "&Arquivo"))
        self.action_new.setText(self.i18n.t("action_new", "&Novo Diagrama"))
        self.action_open_project.setText(self.i18n.t("action_open_project", "&Abrir Projeto..."))
        self.action_save_project.setText(self.i18n.t("action_save_project", "&Salvar Projeto..."))
        self.action_export.setText(self.i18n.t("action_export", "&Exportar como Imagem..."))
        self.action_exit.setText(self.i18n.t("action_exit", "&Sair"))

        self.menu_edit.setTitle(self.i18n.t("menu_edit", "&Editar"))
        self.action_delete.setText(self.i18n.t("action_delete", "&Excluir Selecionado"))

        self.menu_diagram.setTitle(self.i18n.t("menu_diagram", "&Diagrama"))
        self.action_add_node.setText(self.i18n.t("action_add_node", "Adicionar &Nó"))
        if hasattr(self, "connection_menu"):
            self.connection_menu.setTitle(self.i18n.t("menu_connections", "Conexões UML"))
        self.update_connection_button_text()

        self.menu_language.setTitle(self.i18n.t("menu_language", "&Idioma"))
        self.menu_help.setTitle(self.i18n.t("menu_help", "Aj&uda"))
        self.action_about.setText(self.i18n.t("action_about", "&Sobre o PyDiagram"))

        self.toolbar.setWindowTitle(self.i18n.t("toolbar_tools", "Ferramentas"))

        if hasattr(self, "sidebar_dock"):
            self.sidebar_dock.setWindowTitle(self.i18n.t("explorer_title", "Explorador de Modelos"))
            self.sidebar_dock.toggleViewAction().setText(
                self.i18n.t("action_toggle_sidebar", "Exibir Explorador / Propriedades")
            )
        if hasattr(self, "tree_widget"):
            self.tree_widget.setHeaderLabels([self.i18n.t("explorer_title", "Explorador de Modelos")])
        if hasattr(self, "prop_group"):
            self.prop_group.setTitle(self.i18n.t("properties_title", "Properties"))
        if hasattr(self, "minimap_group"):
            self.minimap_group.setTitle(self.i18n.t("minimap_title", "Minimapa"))

        self.statusbar.showMessage(self.i18n.t("status_ready", "Pronto"), 2000)

    retranslateUi = retranslate_ui

    def create_class_at(self, scene_pos: QPointF, title: str = "NovaClasse") -> DiagramNodeItem:
        """Cria e insere um nó UML em coordenadas específicas."""
        node = DiagramNodeItem(
            title=title,
            x=scene_pos.x(),
            y=scene_pos.y(),
            width=160,
            height=100,
        )
        self.scene.addItem(node)
        self.node_counter += 1

        self.scene.clearSelection()
        node.setSelected(True)
        self.update_tree()
        self.populate_properties(node)
        self.statusbar.showMessage(self.i18n.t("status_node_added", "Nó adicionado ao diagrama."), 3000)
        return node

    def on_add_node(self) -> None:
        """Cria um novo nó no centro visível."""
        offset = (self.node_counter * 35) % 200
        node = DiagramNodeItem(
            title=f"Classe_{self.node_counter}",
            x=-80 + offset,
            y=-50 + offset,
            width=160,
            height=100,
        )
        self.scene.addItem(node)
        self.node_counter += 1

        self.scene.clearSelection()
        node.setSelected(True)
        self.update_tree()
        self.populate_properties(node)
        self.statusbar.showMessage(self.i18n.t("status_node_added"), 3000)

    def on_delete_selected(self) -> None:
        """Remove os elementos selecionados com liberação de recursos do Qt e GC."""
        selected_items = self.scene.selectedItems()
        if not selected_items:
            return

        for item in selected_items:
            if isinstance(item, DiagramNodeItem):
                item.remove_all_connections()
                if item.floating_panel:
                    item.hide_floating_panel()
                if item.scene():
                    item.scene().removeItem(item)
                elif self.scene == item.scene():
                    self.scene.removeItem(item)
            elif isinstance(item, DiagramConnectionItem):
                item.detach()
                if item.scene():
                    item.scene().removeItem(item)
                elif self.scene == item.scene():
                    self.scene.removeItem(item)
            elif isinstance(item, WaypointItem):
                item.remove_self()

        self.update_tree()
        self.populate_properties(None)
        self.statusbar.showMessage(self.i18n.t("status_deleted"), 3000)

    def on_clear_diagram(self) -> None:
        """Limpa todo o diagrama e reseta contadores."""
        for item in list(self.scene.items()):
            if isinstance(item, DiagramNodeItem):
                item.remove_all_connections()
                if item.floating_panel:
                    item.hide_floating_panel()
                if item.scene():
                    item.scene().removeItem(item)
                else:
                    self.scene.removeItem(item)
            elif isinstance(item, DiagramConnectionItem):
                item.detach()
                if item.scene():
                    item.scene().removeItem(item)
                else:
                    self.scene.removeItem(item)

        self.scene.clear()
        self.node_counter = 1
        self.update_tree()
        self.populate_properties(None)
        self.statusbar.showMessage(self.i18n.t("action_clear", "Diagrama limpo."), 3000)

    def on_show_about(self) -> None:
        QMessageBox.about(
            self,
            self.i18n.t("about_title", "Sobre o PyDiagram"),
            self.i18n.t("about_text", "PyDiagram - Modelador de Diagramas Open-Source"),
        )

    def export_to_image(self) -> None:
        """Exporta o diagrama renderizado para PNG ou JPG."""
        items_rect = self.scene.itemsBoundingRect()
        if items_rect.isEmpty() or not self.scene.items():
            self.statusbar.showMessage(
                self.i18n.t(
                    "status_export_empty",
                    "O diagrama está vazio. Nenhum item para exportar.",
                ),
                4000,
            )
            return

        dialog_title = self.i18n.t("export_dialog_title", "Exportar como Imagem")
        filters = self.i18n.t(
            "export_filter", "Imagens PNG (*.png);;Imagens JPEG (*.jpg *.jpeg)"
        )
        file_path, selected_filter = QFileDialog.getSaveFileName(
            self,
            dialog_title,
            "diagrama.png",
            filters,
        )
        if not file_path:
            return

        if not (
            file_path.lower().endswith(".png")
            or file_path.lower().endswith(".jpg")
            or file_path.lower().endswith(".jpeg")
        ):
            if "jpg" in selected_filter.lower() or "jpeg" in selected_filter.lower():
                file_path += ".jpg"
            else:
                file_path += ".png"

        padding = 30.0
        source_rect = items_rect.adjusted(-padding, -padding, padding, padding)
        width = max(1, int(math.ceil(source_rect.width())))
        height = max(1, int(math.ceil(source_rect.height())))

        image = QImage(width, height, QImage.Format.Format_ARGB32)
        image.fill(QColor(255, 255, 255))

        painter = QPainter(image)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

            target_rect = QRectF(image.rect())
            self.scene.render(painter, target_rect, source_rect)
        finally:
            painter.end()

        saved = image.save(file_path)
        if saved:
            success_msg = self.i18n.t(
                "status_export_success", f"Diagrama exportado com sucesso: {file_path}"
            ).replace("{path}", file_path)
            self.statusbar.showMessage(success_msg, 5000)
        else:
            QMessageBox.warning(
                self,
                self.i18n.t("export_error_title", "Erro ao Exportar"),
                self.i18n.t("export_error_msg", "Não foi possível salvar o arquivo de imagem."),
            )

    @staticmethod
    def get_default_projects_dir() -> str:
        folder = os.path.join(os.getcwd(), "Projetos_UML")
        os.makedirs(folder, exist_ok=True)
        return folder

    def save_project(self) -> None:
        """Salva todo o diagrama atual em JSON."""
        projects_dir = self.get_default_projects_dir()
        default_file = os.path.join(projects_dir, "projeto_uml.json")
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            self.i18n.t("action_save_project", "Salvar Projeto"),
            default_file,
            "Arquivos JSON (*.json);;Todos os Arquivos (*)",
        )
        if not file_path:
            return

        if not file_path.lower().endswith(".json"):
            file_path += ".json"

        nodes = [it for it in self.scene.items() if isinstance(it, DiagramNodeItem)]
        anchors = [it for it in self.scene.items() if isinstance(it, AnchorItem)]
        connections = [it for it in self.scene.items() if isinstance(it, DiagramConnectionItem)]

        node_id_map: Dict[Any, str] = {}
        nodes_data = []
        for idx, node in enumerate(nodes):
            node_id = f"node_{idx}"
            node_id_map[node] = node_id

            attrs_data = []
            for attr in node.attribute_items:
                attrs_data.append({
                    "text": attr.toPlainText(),
                    "is_italic": attr.font().italic(),
                    "font_family": attr.font().family(),
                    "font_size": attr.font().pointSize(),
                    "color": attr.defaultTextColor().name(),
                })

            methods_data = []
            for method in node.method_items:
                methods_data.append({
                    "text": method.toPlainText(),
                    "is_italic": method.font().italic(),
                    "font_family": method.font().family(),
                    "font_size": method.font().pointSize(),
                    "color": method.defaultTextColor().name(),
                })

            t_font = node.title_item.font()
            nodes_data.append({
                "id": node_id,
                "title": node.title,
                "x": node.pos().x(),
                "y": node.pos().y(),
                "width": node.rect().width(),
                "height": node.rect().height(),
                "is_abstract": node.is_abstract,
                "title_font_family": t_font.family(),
                "title_font_size": t_font.pointSize(),
                "title_color": node.title_item.defaultTextColor().name(),
                "attributes": attrs_data,
                "methods": methods_data,
            })

        anchor_id_map: Dict[AnchorItem, str] = {}
        for idx, anchor in enumerate(anchors):
            anchor_id = f"anchor_{idx}"
            anchor_id_map[anchor] = anchor_id
            node_id_map[anchor] = anchor_id

        conn_id_map: Dict[DiagramConnectionItem, str] = {}
        for idx, conn in enumerate(connections):
            conn_id_map[conn] = f"conn_{idx}"

        anchors_data = []
        for anchor, anchor_id in anchor_id_map.items():
            parent_conn_id = (
                conn_id_map.get(anchor.parent_connection)
                if anchor.parent_connection in conn_id_map
                else None
            )
            anchors_data.append({
                "id": anchor_id,
                "parent_connection_id": parent_conn_id,
                "x": anchor.pos().x(),
                "y": anchor.pos().y(),
            })

        connections_data = []
        for conn in connections:
            if conn.source_node in node_id_map and conn.target_node in node_id_map:
                conn_type = getattr(conn, "connection_type", "Association")
                waypoints_list = [
                    {"x": float(wp.x()), "y": float(wp.y())}
                    for wp in getattr(conn, "waypoints", [])
                ]
                conn_entry: Dict[str, Any] = {
                    "id": conn_id_map[conn],
                    "source_id": node_id_map[conn.source_node],
                    "target_id": node_id_map[conn.target_node],
                    "connection_type": conn_type,
                    "type": conn_type,
                    "end1_props": dict(getattr(conn, "end1_props", {})),
                    "end2_props": dict(getattr(conn, "end2_props", {})),
                    "waypoints": waypoints_list,
                }
                if conn.anchor_item and conn.anchor_item in anchor_id_map:
                    conn_entry["anchor_id"] = anchor_id_map[conn.anchor_item]
                connections_data.append(conn_entry)

        project_data = {
            "version": "1.0",
            "generator": "PyDiagram",
            "nodes": nodes_data,
            "anchors": anchors_data,
            "connections": connections_data,
        }

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(project_data, f, indent=2, ensure_ascii=False)
            self.statusbar.showMessage(f"Projeto salvo com sucesso: {file_path}", 4000)
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Erro ao Salvar",
                f"Ocorreu um erro ao salvar o projeto:\n{exc}",
            )

    def load_project(self) -> None:
        """Carrega projeto JSON e recria a cena do diagrama."""
        projects_dir = self.get_default_projects_dir()
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            self.i18n.t("action_open_project", "Abrir Projeto"),
            projects_dir,
            "Arquivos JSON (*.json);;Todos os Arquivos (*)",
        )
        if not file_path:
            return

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                project_data = json.load(f)
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Erro ao Abrir",
                f"Não foi possível abrir o arquivo JSON:\n{exc}",
            )
            return

        nodes_data = project_data.get("nodes", [])
        connections_data = project_data.get("connections", [])

        self.scene.clear()
        self.current_property_item = None
        self.node_counter = 1

        created_nodes: Dict[str, DiagramNodeItem] = {}

        for n_data in nodes_data:
            node_id = n_data.get("id", "")
            title = n_data.get("title", "Classe")
            x = float(n_data.get("x", 0))
            y = float(n_data.get("y", 0))
            w = float(n_data.get("width", 170))
            h = float(n_data.get("height", 120))
            is_abstract = bool(n_data.get("is_abstract", False))

            node = DiagramNodeItem(
                title=title,
                x=x,
                y=y,
                width=w,
                height=h,
                attributes=[],
                methods=[],
                is_abstract=is_abstract,
            )

            for old_attr in list(node.attribute_items):
                if old_attr.scene():
                    old_attr.scene().removeItem(old_attr)
                old_attr.setParentItem(None)
            node.attribute_items.clear()
            for a_item in n_data.get("attributes", []):
                if isinstance(a_item, dict):
                    txt = a_item.get("text", "+ atributo: tipo")
                    attr = EditableTextItem(txt, parent=node, item_type="attribute")
                    attr.setParentItem(node)
                    font = attr.font()
                    if a_item.get("font_family"):
                        font.setFamily(a_item["font_family"])
                    if a_item.get("font_size"):
                        font.setPointSize(int(a_item["font_size"]))
                    if a_item.get("is_italic"):
                        font.setItalic(True)
                    attr.setFont(font)
                    if a_item.get("color"):
                        attr.setDefaultTextColor(QColor(a_item["color"]))
                else:
                    attr = EditableTextItem(str(a_item), parent=node, item_type="attribute")
                    attr.setParentItem(node)
                node.attribute_items.append(attr)

            for old_meth in list(node.method_items):
                if old_meth.scene():
                    old_meth.scene().removeItem(old_meth)
                old_meth.setParentItem(None)
            node.method_items.clear()
            for m_item in n_data.get("methods", []):
                if isinstance(m_item, dict):
                    txt = m_item.get("text", "+ operacao()")
                    meth = EditableTextItem(txt, parent=node, item_type="method")
                    meth.setParentItem(node)
                    font = meth.font()
                    if m_item.get("font_family"):
                        font.setFamily(m_item["font_family"])
                    if m_item.get("font_size"):
                        font.setPointSize(int(m_item["font_size"]))
                    if m_item.get("is_italic"):
                        font.setItalic(True)
                    meth.setFont(font)
                    if m_item.get("color"):
                        meth.setDefaultTextColor(QColor(m_item["color"]))
                else:
                    meth = EditableTextItem(str(m_item), parent=node, item_type="method")
                    meth.setParentItem(node)
                node.method_items.append(meth)

            if n_data.get("title_font_family") or n_data.get("title_font_size"):
                t_font = node.title_item.font()
                if n_data.get("title_font_family"):
                    t_font.setFamily(n_data["title_font_family"])
                if n_data.get("title_font_size"):
                    t_font.setPointSize(int(n_data["title_font_size"]))
                t_font.setBold(True)
                t_font.setItalic(is_abstract)
                node.title_item.setFont(t_font)
            if n_data.get("title_color"):
                node.title_item.setDefaultTextColor(QColor(n_data["title_color"]))

            node.update_layout()
            self.scene.addItem(node)
            created_nodes[node_id] = node

        anchors_data = project_data.get("anchors", [])
        created_anchors: Dict[str, AnchorItem] = {}
        created_connections: Dict[str, DiagramConnectionItem] = {}
        deferred_connections: List[Dict[str, Any]] = []

        # 1ª passagem de conexões: cria conexões entre classes (DiagramNodeItem)
        for idx, c_data in enumerate(connections_data):
            src_id = c_data.get("source_id")
            tgt_id = c_data.get("target_id")
            if src_id in created_nodes and tgt_id in created_nodes:
                conn_id = c_data.get("id", f"conn_{idx}")
                conn_type = c_data.get("connection_type") or c_data.get("type", "Association")
                if conn_type == "inheritance":
                    conn_type = "Generalization"
                end1_props = c_data.get("end1_props")
                end2_props = c_data.get("end2_props")
                src_node = created_nodes[src_id]
                tgt_node = created_nodes[tgt_id]
                conn = DiagramConnectionItem(
                    src_node,
                    tgt_node,
                    connection_type=conn_type,
                    end1_props=end1_props if isinstance(end1_props, dict) else None,
                    end2_props=end2_props if isinstance(end2_props, dict) else None,
                )
                self.scene.addItem(conn)
                for wp_data in c_data.get("waypoints", []):
                    if isinstance(wp_data, dict) and "x" in wp_data and "y" in wp_data:
                        conn.add_waypoint(
                            QPointF(float(wp_data["x"]), float(wp_data["y"])),
                            sort_by_projection=False,
                        )
                created_connections[conn_id] = conn

                anchor_id = c_data.get("anchor_id")
                if anchor_id:
                    anchor = conn.ensure_anchor_item()
                    created_anchors[anchor_id] = anchor
            else:
                deferred_connections.append(c_data)

        # Garante que quaisquer âncoras listadas em "anchors" sejam recriadas
        for a_data in anchors_data:
            a_id = a_data.get("id")
            parent_conn_id = a_data.get("parent_connection_id")
            if a_id and a_id not in created_anchors:
                parent_conn = created_connections.get(parent_conn_id) if parent_conn_id else None
                if parent_conn is not None:
                    anchor = parent_conn.ensure_anchor_item()
                else:
                    anchor = AnchorItem(
                        float(a_data.get("x", 0.0)),
                        float(a_data.get("y", 0.0)),
                    )
                    self.scene.addItem(anchor)
                created_anchors[a_id] = anchor

        # 2ª passagem de conexões: cria conexões ligadas a âncoras (Association Class)
        all_endpoints: Dict[str, Any] = {**created_nodes, **created_anchors}
        for c_data in deferred_connections:
            src_id = c_data.get("source_id")
            tgt_id = c_data.get("target_id")
            conn_type = c_data.get("connection_type") or c_data.get("type", "Association Class")
            end1_props = c_data.get("end1_props")
            end2_props = c_data.get("end2_props")
            src_obj = all_endpoints.get(src_id)
            tgt_obj = all_endpoints.get(tgt_id)
            if src_obj and tgt_obj:
                conn = DiagramConnectionItem(
                    src_obj,
                    tgt_obj,
                    connection_type=conn_type,
                    end1_props=end1_props if isinstance(end1_props, dict) else None,
                    end2_props=end2_props if isinstance(end2_props, dict) else None,
                )
                self.scene.addItem(conn)
                for wp_data in c_data.get("waypoints", []):
                    if isinstance(wp_data, dict) and "x" in wp_data and "y" in wp_data:
                        conn.add_waypoint(
                            QPointF(float(wp_data["x"]), float(wp_data["y"])),
                            sort_by_projection=False,
                        )
                if isinstance(tgt_obj, AnchorItem) and tgt_obj.parent_connection:
                    tgt_obj.parent_connection.association_class_link = conn
                    if isinstance(src_obj, DiagramNodeItem):
                        tgt_obj.parent_connection.association_class_node = src_obj
                elif isinstance(src_obj, AnchorItem) and src_obj.parent_connection:
                    src_obj.parent_connection.association_class_link = conn
                    if isinstance(tgt_obj, DiagramNodeItem):
                        src_obj.parent_connection.association_class_node = tgt_obj

        # Recalcula o layout de todos os nós reconstruídos
        for node in created_nodes.values():
            node.update_layout()

        self.node_counter = len(created_nodes) + 1
        self.update_tree()
        self.populate_properties(None)
        if hasattr(self, "minimap_view") and self.minimap_view:
            self.minimap_view.update_minimap()

        self.statusbar.showMessage(f"Projeto carregado com sucesso: {file_path}", 4000)

    def create_initial_example(self) -> None:
        """Inicialização limpa: a cena inicia sem nós UML ou conexões pré-criadas."""
        pass


# ==============================================================================
# Ponto de Entrada da Aplicação
# ==============================================================================
def main() -> None:
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
