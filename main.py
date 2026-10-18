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
    QMessageBox,
    QPushButton,
    QSpinBox,
    QSplitter,
    QStatusBar,
    QToolBar,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
)

# Importações dos módulos gráficos e de componentes
from uml_items import (
    DiagramConnectionItem,
    DiagramNodeItem,
    EditableTextItem,
    FloatingEditPanel,
    InlineActionPanel,
    UMLMemberItem,
    get_main_window,
)
from ui_components import (
    DiagramScene,
    DiagramView,
    MinimapView,
)

# Re-exportações para compatibilidade reversa com scripts e testes existentes
__all__ = [
    "I18nManager",
    "DiagramConnectionItem",
    "EditableTextItem",
    "InlineActionPanel",
    "FloatingEditPanel",
    "DiagramNodeItem",
    "UMLMemberItem",
    "DiagramScene",
    "DiagramView",
    "MinimapView",
    "MainWindow",
    "get_main_window",
    "main",
]


# ==============================================================================
# 1. Gerenciador de Internacionalização (i18n)
# ==============================================================================
class I18nManager:
    """Gerencia traduções e troca de idioma dinamicamente a partir de arquivos JSON."""

    def __init__(self, locales_dir: Path, default_lang: str = "pt-BR") -> None:
        self.locales_dir = locales_dir
        self.translations: Dict[str, Dict[str, str]] = {}
        self.current_lang = default_lang
        self.load_locales()

    def load_locales(self) -> None:
        """Carrega todos os arquivos .json da pasta locales."""
        if not self.locales_dir.exists():
            return

        for file_path in self.locales_dir.glob("*.json"):
            lang_code = file_path.stem
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    self.translations[lang_code] = json.load(f)
            except Exception as exc:
                print(f"[i18n] Erro ao carregar '{file_path}': {exc}", file=sys.stderr)

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

        # Internacionalização
        locales_dir = Path(__file__).resolve().parent / "locales"
        self.i18n = I18nManager(locales_dir, default_lang="pt-BR")

        # Cena e Canvas com otimizações ativas
        self.scene = DiagramScene(self)
        self.view = DiagramView(self.scene, self)

        # Estados internos e controle de concorrência de propriedades
        self._is_populating_properties: bool = False
        self._is_applying_properties: bool = False
        self.current_property_item: Optional[Any] = None
        self.current_prop_color: QColor = QColor(51, 65, 85)
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

        self.prop_layout.addRow("name", self.prop_name_edit)
        self.prop_layout.addRow("visibility", self.prop_visibility_combo)
        self.prop_layout.addRow("isAbstract", self.prop_abstract_check)
        self.prop_layout.addRow("font", self.prop_font_combo)
        self.prop_layout.addRow("size", self.prop_size_spin)
        self.prop_layout.addRow("color", self.prop_color_btn)

        # Conecta sinais do formulário apenas uma vez
        self.prop_name_edit.textEdited.connect(self.apply_properties)
        self.prop_visibility_combo.currentIndexChanged.connect(self.apply_properties)
        self.prop_abstract_check.stateChanged.connect(self.apply_properties)
        self.prop_font_combo.currentFontChanged.connect(self.apply_properties)
        self.prop_size_spin.valueChanged.connect(self.apply_properties)
        self.prop_color_btn.clicked.connect(self.choose_property_color)

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

    def populate_properties(self, selected_item: Optional[Any]) -> None:
        """Preenche o formulário de propriedades com base no item ativo."""
        self._is_populating_properties = True
        try:
            self.current_property_item = selected_item
            if selected_item is None:
                self.prop_name_edit.setEnabled(False)
                self.prop_visibility_combo.setEnabled(False)
                self.prop_abstract_check.setEnabled(False)
                self.prop_font_combo.setEnabled(False)
                self.prop_size_spin.setEnabled(False)
                self.prop_color_btn.setEnabled(False)
                self.prop_name_edit.clear()
                self.prop_visibility_combo.setCurrentIndex(3)
                self.prop_abstract_check.setChecked(False)
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
        selected_nodes = [
            it for it in self.scene.selectedItems() if isinstance(it, DiagramNodeItem)
        ]
        if selected_nodes:
            node = selected_nodes[0]
            self.populate_properties(node)
            self.select_in_tree(node)
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
        self.scene.connection_mode_changed.connect(self.action_connection_mode.setChecked)

        self.action_lang_pt = QAction("Português (pt-BR)", self)
        self.action_lang_pt.setCheckable(True)
        self.action_lang_pt.setChecked(True)
        self.action_lang_pt.triggered.connect(lambda: self.switch_language("pt-BR"))

        self.action_lang_en = QAction("English (en-US)", self)
        self.action_lang_en.setCheckable(True)
        self.action_lang_en.setChecked(False)
        self.action_lang_en.triggered.connect(lambda: self.switch_language("en-US"))

        self.lang_action_group = QActionGroup(self)
        self.lang_action_group.addAction(self.action_lang_pt)
        self.lang_action_group.addAction(self.action_lang_en)
        self.lang_action_group.setExclusive(True)

        self.action_about = QAction(self)
        self.action_about.triggered.connect(self.on_show_about)

    def on_connection_mode_toggled(self, checked: bool) -> None:
        self.scene.connection_mode = checked
        if checked:
            self.statusbar.showMessage(
                self.i18n.t(
                    "status_connection_mode_active",
                    "Modo de Conexão ativo: Clique em uma classe e arraste até outra.",
                ),
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
        self.menu_diagram.addAction(self.action_connection_mode)
        if hasattr(self, "sidebar_dock"):
            self.menu_diagram.addSeparator()
            self.menu_diagram.addAction(self.sidebar_dock.toggleViewAction())

        self.menu_language = menubar.addMenu("")
        self.menu_language.addAction(self.action_lang_pt)
        self.menu_language.addAction(self.action_lang_en)

        self.menu_help = menubar.addMenu("")
        self.menu_help.addAction(self.action_about)

    def create_toolbar(self) -> None:
        """Cria a barra de ferramentas principal."""
        self.toolbar = QToolBar(self)
        self.toolbar.setMovable(False)
        self.addToolBar(self.toolbar)

        self.toolbar.addAction(self.action_open_project)
        self.toolbar.addAction(self.action_save_project)
        self.toolbar.addSeparator()
        self.toolbar.addAction(self.action_add_node)
        self.toolbar.addAction(self.action_connection_mode)
        self.toolbar.addSeparator()
        self.toolbar.addAction(self.action_export)
        self.toolbar.addAction(self.action_delete)

    def create_statusbar(self) -> None:
        self.statusbar = QStatusBar(self)
        self.setStatusBar(self.statusbar)

    def switch_language(self, lang_code: str) -> None:
        if self.i18n.set_language(lang_code):
            self.retranslate_ui()

    def retranslate_ui(self) -> None:
        """Aplica os textos traduzidos à janela e seus componentes."""
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
        self.action_connection_mode.setText(self.i18n.t("action_connection_mode", "Conectar Classes"))

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
        if hasattr(self, "minimap_group"):
            self.minimap_group.setTitle(self.i18n.t("minimap_title", "Minimapa"))

        self.statusbar.showMessage(self.i18n.t("status_ready", "Pronto"), 2000)

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
        connections = [it for it in self.scene.items() if isinstance(it, DiagramConnectionItem)]

        node_id_map: Dict[DiagramNodeItem, str] = {}
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

        connections_data = []
        for conn in connections:
            if conn.source_node in node_id_map and conn.target_node in node_id_map:
                connections_data.append({
                    "source_id": node_id_map[conn.source_node],
                    "target_id": node_id_map[conn.target_node],
                    "type": "inheritance",
                })

        project_data = {
            "version": "1.0",
            "generator": "PyDiagram",
            "nodes": nodes_data,
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

        for c_data in connections_data:
            src_id = c_data.get("source_id")
            tgt_id = c_data.get("target_id")
            src_node = created_nodes.get(src_id)
            tgt_node = created_nodes.get(tgt_id)
            if src_node and tgt_node:
                conn = DiagramConnectionItem(src_node, tgt_node)
                self.scene.addItem(conn)

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
