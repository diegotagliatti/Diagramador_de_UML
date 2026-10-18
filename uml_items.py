"""
Módulo de Itens Gráficos UML (uml_items.py)
Contém os nós de classe, itens de texto editáveis, conexões de herança
e painéis flutuantes de ação em linha para o PyDiagram.
"""

from __future__ import annotations
import math
import re
import unicodedata
from typing import Any, List, Optional, Tuple

from PyQt6.QtCore import QLineF, QPointF, QRectF, Qt
from PyQt6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QPainter,
    QPainterPath,
    QPen,
    QPolygonF,
    QTextCursor,
)
from PyQt6.QtWidgets import (
    QGraphicsItem,
    QGraphicsLineItem,
    QGraphicsProxyWidget,
    QGraphicsRectItem,
    QGraphicsSceneContextMenuEvent,
    QGraphicsSceneMouseEvent,
    QGraphicsTextItem,
    QHBoxLayout,
    QMenu,
    QPushButton,
    QWidget,
)


def get_main_window(item: Optional[QGraphicsItem]) -> Optional[Any]:
    """Recupera a instância da janela principal (MainWindow) a partir de um QGraphicsItem."""
    if not item:
        return None
    scene = item.scene()
    if scene:
        for view in scene.views():
            win = view.window()
            if win is not None and win.__class__.__name__ == "MainWindow":
                return win
    return None


class DiagramConnectionItem(QGraphicsLineItem):
    """
    Representa uma linha de conexão de herança UML (Generalização).
    - Conecta as bordas dos nós (sceneBoundingRect) utilizando interseções com QLineF.
    - O nó de destino (target_node) é a classe Pai/Superclasse.
    - Desenha uma seta com um triângulo fechado branco na extremidade que toca no nó Pai.
    """

    def __init__(
        self,
        source_node: DiagramNodeItem,
        target_node: DiagramNodeItem,
        parent: Optional[QGraphicsItem] = None,
    ) -> None:
        super().__init__(parent)
        self.source_node = source_node
        self.target_node = target_node

        self.source_node.add_connection(self)
        self.target_node.add_connection(self)

        self.setPen(
            QPen(QColor(70, 80, 95), 1.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        )
        self.setZValue(-1)  # Mantém a linha sempre atrás dos nós
        self.setFlags(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)

        self.arrow_size = 15.0  # Comprimento do triângulo de herança
        self.update_position()

    def detach(self) -> None:
        """Remove a referência desta conexão dos nós de origem e destino."""
        if self in self.source_node.connections:
            self.source_node.connections.remove(self)
        if self in self.target_node.connections:
            self.target_node.connections.remove(self)

    @staticmethod
    def intersect(line1: QLineF, line2: QLineF) -> Tuple[bool, Optional[QPointF]]:
        """Calcula a interseção entre duas linhas usando QLineF."""
        if hasattr(line1, "intersects"):
            inter_type, pt = line1.intersects(line2)
            if inter_type == QLineF.IntersectionType.BoundedIntersection:
                return True, pt
        elif hasattr(line1, "intersect"):
            pt = QPointF()
            inter_type = line1.intersect(line2, pt)
            if inter_type == QLineF.IntersectionType.BoundedIntersection:
                return True, pt
        return False, None

    def get_rect_intersection(
        self, center_line: QLineF, rect: QRectF
    ) -> Optional[QPointF]:
        """Calcula o ponto onde a linha entre os centros intersecta as bordas do nó."""
        edges = [
            QLineF(rect.topLeft(), rect.topRight()),
            QLineF(rect.topRight(), rect.bottomRight()),
            QLineF(rect.bottomRight(), rect.bottomLeft()),
            QLineF(rect.bottomLeft(), rect.topLeft()),
        ]
        for edge in edges:
            has_inter, pt = self.intersect(center_line, edge)
            if has_inter and pt is not None:
                return pt
        return None

    def update_position(self) -> None:
        """Recalcula os pontos inicial e final da linha com base nas bordas dos nós."""
        if not self.source_node or not self.target_node:
            return

        source_rect = self.source_node.sceneBoundingRect()
        target_rect = self.target_node.sceneBoundingRect()

        c1 = source_rect.center()
        c2 = target_rect.center()

        center_line = QLineF(c1, c2)
        if center_line.length() == 0:
            self.setLine(center_line)
            return

        p1 = self.get_rect_intersection(center_line, source_rect) or c1
        p2 = self.get_rect_intersection(center_line, target_rect) or c2

        self.setLine(QLineF(self.mapFromScene(p1), self.mapFromScene(p2)))

    def boundingRect(self) -> QRectF:
        """Expande os limites para garantir renderização correta do triângulo da seta."""
        extra = (self.pen().widthF() + self.arrow_size) / 2.0 + 8.0
        return (
            QRectF(self.line().p1(), self.line().p2())
            .normalized()
            .adjusted(-extra, -extra, extra, extra)
        )

    def shape(self) -> QPainterPath:
        """Define a área de clique incluindo a linha e o triângulo de herança."""
        path = super().shape()
        line = self.line()
        if line.length() > 0:
            dx = line.dx()
            dy = line.dy()
            length = line.length()
            ux = dx / length
            uy = dy / length
            nx = -uy
            ny = ux

            tip = line.p2()
            base_center = QPointF(
                tip.x() - ux * self.arrow_size, tip.y() - uy * self.arrow_size
            )
            half_w = self.arrow_size * 0.55
            c1 = QPointF(base_center.x() + nx * half_w, base_center.y() + ny * half_w)
            c2 = QPointF(base_center.x() - nx * half_w, base_center.y() - ny * half_w)

            arrow_poly = QPolygonF([tip, c1, c2])
            arrow_path = QPainterPath()
            arrow_path.addPolygon(arrow_poly)
            path.addPath(arrow_path)
        return path

    def paint(self, painter: QPainter, option: Any, widget: Optional[QWidget] = None) -> None:
        """Renderiza a linha de ligação e o triângulo de herança UML."""
        if (
            not self.source_node
            or not self.target_node
            or self.source_node.scene() != self.scene()
            or self.target_node.scene() != self.scene()
        ):
            return

        line = self.line()
        if line.length() == 0:
            return

        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        pen = QPen(self.pen())
        if self.isSelected():
            pen.setColor(QColor(26, 115, 232))
            pen.setStyle(Qt.PenStyle.DashLine)
            pen.setWidthF(2.5)
        else:
            pen.setColor(QColor(70, 80, 95))
            pen.setStyle(Qt.PenStyle.SolidLine)
            pen.setWidthF(1.8)
        painter.setPen(pen)

        p1 = line.p1()
        p2 = line.p2()

        dx = p2.x() - p1.x()
        dy = p2.y() - p1.y()
        length = math.hypot(dx, dy)
        if length == 0:
            return

        ux = dx / length
        uy = dy / length
        nx = -uy
        ny = ux

        arrow_length = self.arrow_size
        arrow_half_width = self.arrow_size * 0.55

        tip = p2
        base_center = QPointF(tip.x() - ux * arrow_length, tip.y() - uy * arrow_length)
        c1 = QPointF(
            base_center.x() + nx * arrow_half_width,
            base_center.y() + ny * arrow_half_width,
        )
        c2 = QPointF(
            base_center.x() - nx * arrow_half_width,
            base_center.y() - ny * arrow_half_width,
        )

        arrow_head = QPolygonF([tip, c1, c2])

        if length > arrow_length:
            painter.drawLine(QLineF(p1, base_center))

        triangle_pen = QPen(pen)
        triangle_pen.setStyle(Qt.PenStyle.SolidLine)
        painter.setPen(triangle_pen)
        painter.setBrush(QBrush(QColor(255, 255, 255)))
        painter.drawPolygon(arrow_head)


class EditableTextItem(QGraphicsTextItem):
    """
    Item de texto editável com suporte a formatação UML inteligente baseada no item_type:
    - 'title': PascalCase, sem acentos nem caracteres especiais, negrito.
    - 'attribute': Garante modificador de visibilidade (+, -, #, ~).
    - 'method': Garante modificador (+, -, #, ~) e fecha com () se necessário.
    """

    def __init__(
        self,
        text: str,
        parent: DiagramNodeItem,
        item_type: str = "title",
        is_italic: bool = False,
        is_title: Optional[bool] = None,
        is_attribute: Optional[bool] = None,
    ) -> None:
        super().__init__(text, parent)
        self.node_parent = parent

        if is_title is not None:
            self.item_type = "title" if is_title else "attribute"
        elif is_attribute is not None:
            self.item_type = "attribute" if is_attribute else "method"
        else:
            self.item_type = str(item_type).lower()

        if self.item_type not in ("title", "attribute", "method"):
            self.item_type = "title"

        if self.item_type == "title":
            font = QFont("Segoe UI", 10, QFont.Weight.Bold)
            if is_italic or (parent and getattr(parent, "is_abstract", False)):
                font.setItalic(True)
            self.setFont(font)
            self.setDefaultTextColor(QColor(30, 41, 59))
        else:
            font = QFont("Segoe UI", 9)
            if is_italic:
                font.setItalic(True)
            self.setFont(font)
            self.setDefaultTextColor(QColor(51, 65, 85))

        self.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)

    @property
    def is_title(self) -> bool:
        return self.item_type == "title"

    @property
    def is_attribute(self) -> bool:
        return self.item_type == "attribute"

    @property
    def is_method(self) -> bool:
        return self.item_type == "method"

    @staticmethod
    def format_uml_title(raw_text: str) -> str:
        """Normaliza caracteres acentuados, remove especiais e aplica PascalCase."""
        normalized = (
            unicodedata.normalize("NFKD", raw_text)
            .encode("ASCII", "ignore")
            .decode("utf-8")
        )
        words = [w for w in re.split(r"[^a-zA-Z0-9]+", normalized) if w]
        if not words:
            return "Classe"
        return "".join(w.capitalize() for w in words)

    def format_text(self, text: str) -> str:
        """Aplica as regras de formatação automática conforme o tipo do item."""
        if self.item_type == "title":
            return self.format_uml_title(text)

        stripped = text.strip()
        if not stripped:
            return "+ novoItem: tipo" if self.item_type == "attribute" else "+ novoMetodo()"

        if stripped[0] in ("+", "-", "#", "~"):
            symbol = stripped[0]
            rest = stripped[1:].strip()
            text = f"{symbol} {rest}" if rest else symbol
        else:
            text = f"+ {stripped}"

        if self.item_type == "method":
            if not text.endswith(")"):
                if "):" not in text and ") :" not in text:
                    text = f"{text}()"

        return text

    def start_editing(self) -> None:
        """Ativa o modo de edição no item de texto com seleção completa."""
        self.setTextInteractionFlags(Qt.TextInteractionFlag.TextEditorInteraction)
        self.setFocus(Qt.FocusReason.MouseFocusReason)
        cursor = self.textCursor()
        cursor.select(QTextCursor.SelectionType.Document)
        self.setTextCursor(cursor)

        win = get_main_window(self)
        if win and hasattr(win, "populate_properties"):
            win.populate_properties(self)
            if hasattr(win, "select_in_tree"):
                win.select_in_tree(self)

        if self.node_parent and self.item_type != "title":
            self.node_parent.show_floating_panel(self)

    def finish_editing(self) -> None:
        """Aplica formatação inteligente, encerra edição e atualiza layout."""
        try:
            raw_text = self.toPlainText()
            formatted = self.format_text(raw_text)
            self.setPlainText(formatted)

            font = self.font()
            if self.item_type == "title":
                font.setBold(True)
                if self.node_parent and getattr(self.node_parent, "is_abstract", False):
                    font.setItalic(True)
            self.setFont(font)

            self.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)

            cursor = self.textCursor()
            cursor.clearSelection()
            self.setTextCursor(cursor)

            if self.node_parent:
                self.node_parent.on_text_edited()
                self.node_parent.hide_floating_panel()

            win = get_main_window(self)
            if win:
                if hasattr(win, "update_tree_item_label"):
                    win.update_tree_item_label(self)
                if hasattr(win, "populate_properties"):
                    win.populate_properties(self)
        except RuntimeError:
            pass

    def focusOutEvent(self, event: Any) -> None:
        self.finish_editing()
        super().focusOutEvent(event)

    def keyPressEvent(self, event: Any) -> None:
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.clearFocus()
            self.finish_editing()
            event.accept()
            return
        super().keyPressEvent(event)

    def mousePressEvent(self, event: Any) -> None:
        if self.textInteractionFlags() == Qt.TextInteractionFlag.NoTextInteraction:
            event.ignore()
            return
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event: Any) -> None:
        self.start_editing()
        if isinstance(event, QGraphicsSceneMouseEvent):
            super().mouseDoubleClickEvent(event)

    def set_visibility(self, symbol: str) -> None:
        """Altera o modificador de visibilidade (+, -, #, ~)."""
        text = self.toPlainText().strip()
        if not text:
            text = "item"

        if text[0] in ("+", "-", "#", "~"):
            rest = text[1:].lstrip()
            new_text = f"{symbol} {rest}" if rest else symbol
        else:
            new_text = f"{symbol} {text}"

        self.setPlainText(new_text)
        if self.node_parent:
            self.node_parent.update_layout()

        win = get_main_window(self)
        if win:
            if hasattr(win, "update_tree_item_label"):
                win.update_tree_item_label(self)
            if (
                hasattr(win, "populate_properties")
                and not getattr(win, "_is_populating_properties", False)
                and not getattr(win, "_is_applying_properties", False)
            ):
                win.populate_properties(self)

    def toggle_abstract(self) -> None:
        """Alterna o estilo itálico (abstração) para este membro."""
        font = self.font()
        font.setItalic(not font.italic())
        self.setFont(font)
        if self.node_parent:
            self.node_parent.update_layout()

        win = get_main_window(self)
        if win:
            if hasattr(win, "update_tree_item_label"):
                win.update_tree_item_label(self)
            if (
                hasattr(win, "populate_properties")
                and not getattr(win, "_is_populating_properties", False)
                and not getattr(win, "_is_applying_properties", False)
            ):
                win.populate_properties(self)

    def contextMenuEvent(self, event: QGraphicsSceneContextMenuEvent) -> None:
        """Menu de contexto do membro."""
        if self.item_type == "title":
            if self.node_parent:
                self.node_parent.contextMenuEvent(event)
            else:
                event.ignore()
            return

        cursor = self.textCursor()
        cursor.select(QTextCursor.SelectionType.Document)
        self.setTextCursor(cursor)

        menu = QMenu()
        action_public = menu.addAction("Tornar Público (+)")
        action_private = menu.addAction("Tornar Privado (-)")
        action_protected = menu.addAction("Tornar Protegido (#)")
        menu.addSeparator()
        action_move_up = menu.addAction("Mover para Cima (↑)")
        action_move_down = menu.addAction("Mover para Baixo (↓)")
        menu.addSeparator()
        action_abstract = menu.addAction("mudar para abstrato (itálico)")
        menu.addSeparator()
        action_remove = menu.addAction("Remover")

        selected = menu.exec(event.screenPos())
        if selected == action_public:
            self.set_visibility("+")
        elif selected == action_private:
            self.set_visibility("-")
        elif selected == action_protected:
            self.set_visibility("#")
        elif selected == action_move_up:
            if self.node_parent:
                self.node_parent.move_member_up(self)
        elif selected == action_move_down:
            if self.node_parent:
                self.node_parent.move_member_down(self)
        elif selected == action_abstract:
            self.toggle_abstract()
        elif selected == action_remove:
            if self.node_parent:
                self.node_parent.remove_member(self)

        if self.textInteractionFlags() != Qt.TextInteractionFlag.TextEditorInteraction:
            cursor = self.textCursor()
            cursor.clearSelection()
            self.setTextCursor(cursor)

        event.accept()


# Alias de compatibilidade
UMLMemberItem = EditableTextItem


class InlineActionPanel(QGraphicsProxyWidget):
    """
    Painel flutuante de ações rápidas (↑, ↓, +, -) que acompanha
    o item de atributo ou método em edição ou selecionado no nó UML.
    """

    def __init__(self, parent_node: DiagramNodeItem) -> None:
        super().__init__(parent_node)
        self.node_parent = parent_node
        self.current_item: Optional[EditableTextItem] = None

        container = QWidget()
        container.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        container.setStyleSheet(
            """
            QWidget {
                background: transparent;
            }
            QPushButton {
                background-color: #3b82f6;
                color: #ffffff;
                font-weight: bold;
                font-size: 11px;
                border: none;
                border-radius: 3px;
                min-width: 18px;
                max-width: 18px;
                min-height: 18px;
                max-height: 18px;
            }
            QPushButton:hover {
                background-color: #2563eb;
            }
            QPushButton:pressed {
                background-color: #1d4ed8;
            }
            QPushButton#btn_add:hover {
                background-color: #10b981;
            }
            QPushButton#btn_add:pressed {
                background-color: #059669;
            }
            QPushButton#btn_remove:hover {
                background-color: #ef4444;
            }
            QPushButton#btn_remove:pressed {
                background-color: #dc2626;
            }
            """
        )
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        self.btn_up = QPushButton("↑", container)
        self.btn_up.setToolTip("Mover para Cima")
        self.btn_up.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_up.clicked.connect(self.on_move_up)

        self.btn_down = QPushButton("↓", container)
        self.btn_down.setToolTip("Mover para Baixo")
        self.btn_down.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_down.clicked.connect(self.on_move_down)

        self.btn_add = QPushButton("+", container)
        self.btn_add.setObjectName("btn_add")
        self.btn_add.setToolTip("Adicionar Item")
        self.btn_add.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_add.clicked.connect(self.on_add)

        self.btn_remove = QPushButton("-", container)
        self.btn_remove.setObjectName("btn_remove")
        self.btn_remove.setToolTip("Remover Item")
        self.btn_remove.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_remove.clicked.connect(self.on_remove)

        layout.addWidget(self.btn_up)
        layout.addWidget(self.btn_down)
        layout.addWidget(self.btn_add)
        layout.addWidget(self.btn_remove)

        self.setWidget(container)
        self.setZValue(100)
        self.hide()

    def on_move_up(self) -> None:
        if self.current_item and self.node_parent:
            self.node_parent.move_member_up(self.current_item)

    def on_move_down(self) -> None:
        if self.current_item and self.node_parent:
            self.node_parent.move_member_down(self.current_item)

    def on_add(self) -> None:
        """Adiciona novo membro com hierarquia segura (setParentItem) logo abaixo do atual."""
        item = self.current_item
        if not item or not self.node_parent:
            return

        target_list: Optional[List[EditableTextItem]] = None
        item_type: str = ""
        default_text: str = ""

        if item in self.node_parent.attribute_items:
            target_list = self.node_parent.attribute_items
            item_type = "attribute"
            default_text = "+ novoItem: tipo"
        elif item in self.node_parent.method_items:
            target_list = self.node_parent.method_items
            item_type = "method"
            default_text = "+ novoMetodo()"

        if target_list is None or item not in target_list:
            return

        idx = target_list.index(item)
        novo_item = EditableTextItem(
            default_text, parent=self.node_parent, item_type=item_type
        )
        novo_item.setParentItem(self.node_parent)

        target_list.insert(idx + 1, novo_item)
        self.node_parent.update_layout()

        win = get_main_window(self.node_parent)
        if win and hasattr(win, "update_tree"):
            win.update_tree()

        novo_item.start_editing()

    on_add_item = on_add

    def on_remove(self) -> None:
        """Remove o item em segurança (Passos 1 a 5) prevenindo falhas de C++ object deleted."""
        # Passo 1: Esconde o painel flutuante PRIMEIRO
        self.hide()
        item = self.current_item
        self.current_item = None

        if not item or not self.node_parent:
            return

        if self.node_parent.floating_panel:
            self.node_parent.floating_panel.current_item = None

        # Passo 2: Limpa seleção e foco
        try:
            item.clearFocus()
            cursor = item.textCursor()
            if cursor.hasSelection():
                cursor.clearSelection()
                item.setTextCursor(cursor)
            if item.isSelected():
                item.setSelected(False)
        except RuntimeError:
            pass

        win = get_main_window(self.node_parent)
        if win and getattr(win, "current_property_item", None) == item:
            win.populate_properties(self.node_parent)

        # Passo 3: Remove da lista interna
        target_list: Optional[List[EditableTextItem]] = None
        if item in self.node_parent.attribute_items:
            target_list = self.node_parent.attribute_items
        elif item in self.node_parent.method_items:
            target_list = self.node_parent.method_items

        if target_list and item in target_list:
            target_list.remove(item)

        # Passo 4: Remove da cena e desvincula
        scene = self.node_parent.scene() or item.scene()
        if scene and item.scene() == scene:
            scene.removeItem(item)
        elif item.scene():
            item.scene().removeItem(item)
        item.setParentItem(None)

        # Passo 5: Recalcula o layout do nó
        self.node_parent.update_layout()

        if win and hasattr(win, "update_tree"):
            win.update_tree()

    on_remove_item = on_remove


# Alias de compatibilidade
FloatingEditPanel = InlineActionPanel


class DiagramNodeItem(QGraphicsRectItem):
    """
    Representa uma classe UML com 3 compartimentos (Título, Atributos, Operações),
    menus de contexto ricos e auto-redimensionamento dinâmico.
    """

    def __init__(
        self,
        title: str = "Classe",
        x: float = 0,
        y: float = 0,
        width: float = 170,
        height: float = 120,
        parent: Optional[QGraphicsItem] = None,
        attributes: str | List[str] = "+ atributo: tipo",
        methods: str | List[str] = "+ operacao(): void",
        is_abstract: bool = False,
    ) -> None:
        super().__init__(0, 0, width, height, parent)
        self.connections: List[DiagramConnectionItem] = []
        self.is_abstract = is_abstract
        self.floating_panel: Optional[InlineActionPanel] = None

        self.setPos(x, y)

        self.setFlags(
            QGraphicsItem.GraphicsItemFlag.ItemIsMovable
            | QGraphicsItem.GraphicsItemFlag.ItemIsSelectable
            | QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges
        )

        # Otimização de renderização em cache
        self.setCacheMode(QGraphicsItem.CacheMode.DeviceCoordinateCache)

        self.bg_color = QColor(255, 255, 255)
        self.header_color = QColor(240, 244, 250)
        self.border_color = QColor(100, 116, 139)
        self.selected_color = QColor(26, 115, 232)

        self.header_height = 34.0
        self.attrs_height = 36.0
        self.methods_height = 36.0

        # 1. Título
        formatted_title = EditableTextItem.format_uml_title(title)
        self.title_item = EditableTextItem(
            formatted_title, parent=self, item_type="title"
        )
        self.title_item.setParentItem(self)
        if self.is_abstract:
            font = self.title_item.font()
            font.setItalic(True)
            self.title_item.setFont(font)

        # 2. Atributos
        self.attribute_items: List[EditableTextItem] = []
        if attributes is None:
            attr_lines = ["+ atributo: tipo"]
        elif isinstance(attributes, str):
            attr_lines = [l.strip() for l in attributes.splitlines() if l.strip()]
        elif isinstance(attributes, list):
            attr_lines = list(attributes)
        else:
            attr_lines = []

        for line in attr_lines:
            it = EditableTextItem(line, parent=self, item_type="attribute")
            it.setParentItem(self)
            self.attribute_items.append(it)

        # 3. Métodos
        self.method_items: List[EditableTextItem] = []
        if methods is None:
            method_lines = ["+ operacao()"]
        elif isinstance(methods, str):
            method_lines = [l.strip() for l in methods.splitlines() if l.strip()]
        elif isinstance(methods, list):
            method_lines = list(methods)
        else:
            method_lines = []

        for line in method_lines:
            it = EditableTextItem(line, parent=self, item_type="method")
            it.setParentItem(self)
            self.method_items.append(it)

        self.update_layout()

    @property
    def text_item(self) -> EditableTextItem:
        return self.title_item

    @property
    def title(self) -> str:
        return self.title_item.toPlainText()

    @title.setter
    def title(self, value: str) -> None:
        self.title_item.setPlainText(EditableTextItem.format_uml_title(value))
        self.update_layout()

    @property
    def attrs_item(self) -> Optional[EditableTextItem]:
        return self.attribute_items[0] if self.attribute_items else None

    @property
    def methods_item(self) -> Optional[EditableTextItem]:
        return self.method_items[0] if self.method_items else None

    @property
    def inline_action_panel(self) -> Optional[InlineActionPanel]:
        return self.floating_panel

    @inline_action_panel.setter
    def inline_action_panel(self, value: Optional[InlineActionPanel]) -> None:
        self.floating_panel = value

    def add_connection(self, connection: DiagramConnectionItem) -> None:
        if connection not in self.connections:
            self.connections.append(connection)

    def remove_all_connections(self) -> None:
        scene = self.scene()
        for conn in list(self.connections):
            conn.detach()
            if scene and conn.scene() == scene:
                scene.removeItem(conn)
            elif conn.scene():
                conn.scene().removeItem(conn)
        self.connections.clear()

    def itemChange(self, change: QGraphicsItem.GraphicsItemChange, value: Any) -> Any:
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            for conn in self.connections:
                conn.update_position()
        return super().itemChange(change, value)

    def set_abstract(self, is_abstract: bool) -> None:
        self.is_abstract = is_abstract
        font = self.title_item.font()
        font.setBold(True)
        font.setItalic(is_abstract)
        self.title_item.setFont(font)
        self.update_layout()

        win = get_main_window(self)
        if win:
            if hasattr(win, "update_tree_item_label"):
                win.update_tree_item_label(self)
            if (
                hasattr(win, "populate_properties")
                and not getattr(win, "_is_populating_properties", False)
                and not getattr(win, "_is_applying_properties", False)
            ):
                win.populate_properties(self)

    def add_attribute(self, text: str = "+ novoAtributo: tipo") -> EditableTextItem:
        item = EditableTextItem(text, parent=self, item_type="attribute")
        item.setParentItem(self)
        self.attribute_items.append(item)
        self.update_layout()
        win = get_main_window(self)
        if win and hasattr(win, "update_tree"):
            win.update_tree()
        item.start_editing()
        return item

    def add_method(self, text: str = "+ novaOperacao()") -> EditableTextItem:
        item = EditableTextItem(text, parent=self, item_type="method")
        item.setParentItem(self)
        self.method_items.append(item)
        self.update_layout()
        win = get_main_window(self)
        if win and hasattr(win, "update_tree"):
            win.update_tree()
        item.start_editing()
        return item

    def remove_member(self, item: EditableTextItem) -> None:
        """Remove membro com sequência segura de 5 passos."""
        if self.floating_panel:
            self.floating_panel.hide()
            self.floating_panel.current_item = None

        try:
            item.clearFocus()
            cursor = item.textCursor()
            if cursor.hasSelection():
                cursor.clearSelection()
                item.setTextCursor(cursor)
            if item.isSelected():
                item.setSelected(False)
        except RuntimeError:
            pass

        win = get_main_window(self)
        if win and getattr(win, "current_property_item", None) == item:
            win.populate_properties(self)

        if item in self.attribute_items:
            self.attribute_items.remove(item)
        elif item in self.method_items:
            self.method_items.remove(item)

        scene = self.scene() or item.scene()
        if scene and item.scene() == scene:
            scene.removeItem(item)
        elif item.scene():
            item.scene().removeItem(item)
        item.setParentItem(None)

        self.update_layout()

        if win and hasattr(win, "update_tree"):
            win.update_tree()

    def show_floating_panel(self, item: EditableTextItem) -> None:
        if item.item_type == "title":
            self.hide_floating_panel()
            return
        if self.floating_panel is None:
            self.floating_panel = InlineActionPanel(self)
        self.floating_panel.current_item = item
        self.update_floating_panel_pos(item)
        self.floating_panel.show()

    def hide_floating_panel(self) -> None:
        if self.floating_panel:
            self.floating_panel.hide()
            self.floating_panel.current_item = None

    def update_floating_panel_pos(self, item: EditableTextItem) -> None:
        if self.floating_panel and item:
            item_y = item.pos().y()
            panel_x = max(10.0, self.rect().width() - 86.0)
            panel_y = item_y + max(0.0, (item.boundingRect().height() - 20.0) / 2.0)
            self.floating_panel.setPos(panel_x, panel_y)

    show_inline_action_panel = show_floating_panel
    hide_inline_action_panel = hide_floating_panel
    update_inline_action_panel_pos = update_floating_panel_pos

    def move_member_up(self, item: EditableTextItem) -> bool:
        target_list: Optional[List[EditableTextItem]] = None
        if item in self.attribute_items:
            target_list = self.attribute_items
        elif item in self.method_items:
            target_list = self.method_items

        if not target_list or item not in target_list:
            return False

        idx = target_list.index(item)
        if idx > 0:
            target_list[idx], target_list[idx - 1] = target_list[idx - 1], target_list[idx]
            self.update_layout()
            self.update_floating_panel_pos(item)
            win = get_main_window(self)
            if win and hasattr(win, "update_tree"):
                win.update_tree()
            return True
        return False

    def move_member_down(self, item: EditableTextItem) -> bool:
        target_list: Optional[List[EditableTextItem]] = None
        if item in self.attribute_items:
            target_list = self.attribute_items
        elif item in self.method_items:
            target_list = self.method_items

        if not target_list or item not in target_list:
            return False

        idx = target_list.index(item)
        if idx < len(target_list) - 1:
            target_list[idx], target_list[idx + 1] = target_list[idx + 1], target_list[idx]
            self.update_layout()
            self.update_floating_panel_pos(item)
            win = get_main_window(self)
            if win and hasattr(win, "update_tree"):
                win.update_tree()
            return True
        return False

    def contextMenuEvent(self, event: QGraphicsSceneContextMenuEvent) -> None:
        menu = QMenu()
        action_add_attr = menu.addAction("Add Atributo")
        action_add_method = menu.addAction("add método")
        menu.addSeparator()

        action_abstract = menu.addAction("Classe Abstrata")
        action_abstract.setCheckable(True)
        action_abstract.setChecked(self.is_abstract)

        selected = menu.exec(event.screenPos())
        if selected == action_add_attr:
            self.add_attribute()
        elif selected == action_add_method:
            self.add_method()
        elif selected == action_abstract:
            self.set_abstract(action_abstract.isChecked())

        event.accept()

    def mouseDoubleClickEvent(self, event: Optional[QGraphicsSceneMouseEvent]) -> None:
        if event is None:
            self.title_item.start_editing()
            return

        click_y = event.pos().y()

        if click_y <= self.header_height:
            self.title_item.start_editing()
        elif click_y <= (self.header_height + self.attrs_height):
            if self.attribute_items:
                target = min(
                    self.attribute_items,
                    key=lambda it: abs(
                        (it.pos().y() + it.boundingRect().height() / 2.0) - click_y
                    ),
                )
                target.start_editing()
            else:
                self.add_attribute()
        else:
            if self.method_items:
                target = min(
                    self.method_items,
                    key=lambda it: abs(
                        (it.pos().y() + it.boundingRect().height() / 2.0) - click_y
                    ),
                )
                target.start_editing()
            else:
                self.add_method()

        if isinstance(event, QGraphicsSceneMouseEvent):
            super().mouseDoubleClickEvent(event)

    def on_text_edited(self) -> None:
        self.update_layout()

    def update_layout(self) -> None:
        """
        Recálculo sequencial e rigoroso de posições e dimensões da classe UML.
        Garante que nenhum atributo ou método sobreponha coordenadas Y.
        """
        # 1. Preparação Geométrica: avisa o PyQt6 para limpar o desenho e índices anteriores
        self.prepareGeometryChange()

        margem_x: float = 8.0
        padding_y: float = 4.0

        title_rect = self.title_item.boundingRect()
        self.header_height = max(34.0, title_rect.height() + 8.0)

        # 2. Recálculo Sequencial das Posições Y:
        # Inicia logo abaixo da linha separadora do cabeçalho
        current_y: float = self.header_height + padding_y

        # Itera pela lista interna de atributos
        for attr_item in self.attribute_items:
            attr_item.setPos(margem_x, current_y)
            current_y += attr_item.boundingRect().height()

        if not self.attribute_items:
            current_y += 20.0

        # Regista a coordenada exata para desenhar a linha separadora entre atributos e métodos
        self.separator_y: float = current_y + padding_y
        self.attrs_height = self.separator_y - self.header_height

        # Desce o current_y para iniciar os métodos abaixo da linha separadora
        current_y = self.separator_y + padding_y

        # Itera pela lista interna de métodos
        for method_item in self.method_items:
            method_item.setPos(margem_x, current_y)
            current_y += method_item.boundingRect().height()

        if not self.method_items:
            current_y += 20.0

        self.methods_height = current_y - self.separator_y

        # 3. Ajuste do Bounding Rect:
        # Atualiza a altura final envolvendo o valor de current_y com margem inferior
        bottom_margin: float = 8.0
        total_height: float = current_y + bottom_margin

        # Largura suficiente para o maior item com folga para botões do painel flutuante
        max_attr_w = max(
            (it.boundingRect().width() + 92.0 for it in self.attribute_items),
            default=0.0,
        )
        max_method_w = max(
            (it.boundingRect().width() + 92.0 for it in self.method_items),
            default=0.0,
        )
        new_width = max(
            170.0,
            title_rect.width() + 36.0,
            max_attr_w,
            max_method_w,
        )

        self.setRect(0, 0, new_width, total_height)

        # Centraliza o título no cabeçalho
        title_x = (new_width - title_rect.width()) / 2.0
        title_y = max(2.0, (self.header_height - title_rect.height()) / 2.0)
        self.title_item.setPos(title_x, title_y)

        # Reposiciona o painel de ações flutuante se visível
        if self.floating_panel and self.floating_panel.isVisible() and self.floating_panel.current_item:
            self.update_floating_panel_pos(self.floating_panel.current_item)

        # Atualiza conexões conectadas
        for conn in self.connections:
            conn.update_position()

        self.update()

    recalculate_size = update_layout

    def boundingRect(self) -> QRectF:
        """Retorna o retângulo delimitador do nó UML englobando a área do rect() e a borda."""
        pen_w = self.pen().widthF()
        half_pen = pen_w / 2.0
        return self.rect().adjusted(-half_pen, -half_pen, half_pen, half_pen)

    def paint(self, painter: QPainter, option: Any, widget: Optional[QWidget] = None) -> None:
        """Desenha a caixa da classe UML com os 3 compartimentos delimitados."""
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect()

        if self.isSelected():
            border_pen = QPen(self.selected_color, 2.5, Qt.PenStyle.SolidLine)
        else:
            border_pen = QPen(self.border_color, 1.5, Qt.PenStyle.SolidLine)

        # 1. Fundo do corpo
        path = QPainterPath()
        path.addRoundedRect(rect, 8, 8)
        painter.fillPath(path, QBrush(self.bg_color))

        # 2. Cabeçalho
        header_rect = QRectF(rect.x(), rect.y(), rect.width(), self.header_height)
        header_path = QPainterPath()
        header_path.addRoundedRect(header_rect, 8, 8)
        bottom_patch = QRectF(
            rect.x(), rect.y() + self.header_height - 8, rect.width(), 8
        )
        header_path.addRect(bottom_patch)
        painter.fillPath(header_path, QBrush(self.header_color))

        # Linhas divisórias dos compartimentos
        painter.setPen(QPen(self.border_color, 1.0, Qt.PenStyle.SolidLine))
        y_div1 = rect.y() + self.header_height
        painter.drawLine(QPointF(rect.x(), y_div1), QPointF(rect.right(), y_div1))

        sep_y = getattr(self, "separator_y", self.header_height + self.attrs_height)
        y_div2 = rect.y() + sep_y
        painter.drawLine(QPointF(rect.x(), y_div2), QPointF(rect.right(), y_div2))

        # Contorno final
        painter.setPen(border_pen)
        painter.drawPath(path)
