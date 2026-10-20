"""
Módulo de Itens Gráficos UML (uml_items.py)
Contém os nós de classe, itens de texto editáveis, conexões de herança
e painéis flutuantes de ação em linha para o PyDiagram.
"""

from __future__ import annotations
import math
import re
import unicodedata
from typing import Any, Dict, List, Optional, Tuple

from PyQt6.QtCore import QLineF, QPointF, QRectF, Qt
from PyQt6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QPainter,
    QPainterPath,
    QPainterPathStroker,
    QPen,
    QPolygonF,
    QTextCursor,
)
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGraphicsItem,
    QGraphicsLineItem,
    QGraphicsProxyWidget,
    QGraphicsRectItem,
    QGraphicsSceneContextMenuEvent,
    QGraphicsSceneMouseEvent,
    QGraphicsTextItem,
    QGroupBox,
    QHBoxLayout,
    QLineEdit,
    QMenu,
    QPushButton,
    QVBoxLayout,
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


class AnchorItem(QGraphicsRectItem):
    """
    Nó de ancoragem posicionado no ponto médio (midpoint) de uma conexão UML
    para ligar uma Classe Associativa (Association Class).
    """

    def __init__(
        self,
        x: float = 0.0,
        y: float = 0.0,
        parent_connection: Optional[DiagramConnectionItem] = None,
        parent: Optional[QGraphicsItem] = None,
    ) -> None:
        super().__init__(-4.0, -4.0, 8.0, 8.0, parent)
        self.parent_connection: Optional[DiagramConnectionItem] = parent_connection
        self.connections: List[DiagramConnectionItem] = []
        self.setPos(x, y)
        self.setZValue(0)

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

    def paint(
        self, painter: QPainter, option: Any, widget: Optional[QWidget] = None
    ) -> None:
        """Desenha um pequeno ponto discreto no midpoint quando conectado."""
        if not self.connections:
            return
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor(70, 80, 95), 1.2))
        painter.setBrush(QBrush(QColor(70, 80, 95)))
        painter.drawEllipse(QPointF(0.0, 0.0), 3.0, 3.0)
        painter.restore()


# Alias de compatibilidade
ConnectionAnchorItem = AnchorItem


class WaypointItem(QGraphicsRectItem):
    """
    Ponto de controle de roteamento (Waypoint) de uma linha de conexão UML.
    - Quadrado 8x8 centrado na origem (-4, -4, 8, 8), preenchimento branco e borda azul.
    - Móvel, selecionável e notifica alterações de geometria à conexão pai.
    - Duplo clique remove o próprio waypoint da lista da conexão e da cena.
    """

    def __init__(
        self,
        x: float = 0.0,
        y: float = 0.0,
        parent_connection: Optional[DiagramConnectionItem] = None,
        parent: Optional[QGraphicsItem] = None,
    ) -> None:
        super().__init__(-4.0, -4.0, 8.0, 8.0, parent)
        self.parent_connection: Optional[DiagramConnectionItem] = parent_connection

        self.setBrush(QBrush(QColor(255, 255, 255)))
        self.setPen(QPen(QColor(37, 99, 235), 1.5))
        self.setZValue(10)

        self.setFlags(
            QGraphicsItem.GraphicsItemFlag.ItemIsMovable
            | QGraphicsItem.GraphicsItemFlag.ItemIsSelectable
            | QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges
        )
        self.setPos(x, y)

    def itemChange(
        self, change: QGraphicsItem.GraphicsItemChange, value: Any
    ) -> Any:
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            if self.parent_connection is not None:
                self.parent_connection.update_position()
                self.parent_connection.update()
        return super().itemChange(change, value)

    def remove_self(self) -> None:
        """Remove a si próprio da lista de waypoints da conexão e da cena."""
        conn = self.parent_connection
        self.parent_connection = None
        if conn is not None:
            if self in conn.waypoints:
                conn.waypoints.remove(self)
            conn.update_position()
            conn.update()

        scene = self.scene()
        if scene is not None:
            scene.removeItem(self)
        self.setParentItem(None)

    def mouseDoubleClickEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        """Suicídio do waypoint ao receber duplo clique."""
        self.remove_self()
        if event is not None:
            event.accept()


class ConnectionConfigDialog(QDialog):
    """
    Janela de diálogo para configurar as propriedades das Extremidades 1 (Origem)
    e 2 (Destino) de uma conexão UML (Multiplicidade, Nome e Visibilidade).
    """

    MULTIPLICITY_OPTIONS = ["", "1", "0..1", "1..*", "*"]
    VISIBILITY_OPTIONS = ["public", "private", "protected", "package"]

    def __init__(
        self,
        connection: Optional[DiagramConnectionItem] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.connection = connection
        self.setWindowTitle("Configurar Ligação UML")
        self.setMinimumWidth(360)

        main_layout = QVBoxLayout(self)

        # Extremidade 1 (Origem)
        self.group_end1 = QGroupBox("Extremidade 1 (Origem)", self)
        self.form_end1 = QFormLayout(self.group_end1)

        self.end1_mult_combo = QComboBox(self.group_end1)
        self.end1_mult_combo.setEditable(True)
        self.end1_mult_combo.addItems(self.MULTIPLICITY_OPTIONS)

        self.end1_name_edit = QLineEdit(self.group_end1)
        self.end1_name_edit.setPlaceholderText("Papel / nome na origem...")

        self.end1_vis_combo = QComboBox(self.group_end1)
        self.end1_vis_combo.addItems(self.VISIBILITY_OPTIONS)

        self.form_end1.addRow("Multiplicidade:", self.end1_mult_combo)
        self.form_end1.addRow("Nome:", self.end1_name_edit)
        self.form_end1.addRow("Visibilidade:", self.end1_vis_combo)

        # Extremidade 2 (Destino)
        self.group_end2 = QGroupBox("Extremidade 2 (Destino)", self)
        self.form_end2 = QFormLayout(self.group_end2)

        self.end2_mult_combo = QComboBox(self.group_end2)
        self.end2_mult_combo.setEditable(True)
        self.end2_mult_combo.addItems(self.MULTIPLICITY_OPTIONS)

        self.end2_name_edit = QLineEdit(self.group_end2)
        self.end2_name_edit.setPlaceholderText("Papel / nome no destino...")

        self.end2_vis_combo = QComboBox(self.group_end2)
        self.end2_vis_combo.addItems(self.VISIBILITY_OPTIONS)

        self.form_end2.addRow("Multiplicidade:", self.end2_mult_combo)
        self.form_end2.addRow("Nome:", self.end2_name_edit)
        self.form_end2.addRow("Visibilidade:", self.end2_vis_combo)

        main_layout.addWidget(self.group_end1)
        main_layout.addWidget(self.group_end2)

        # Botões Confirmar / Cancelar
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            self,
        )
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        main_layout.addWidget(self.button_box)

        if self.connection is not None:
            self._load_from_connection(self.connection)

    def _load_from_connection(self, conn: DiagramConnectionItem) -> None:
        e1 = conn.end1_props
        e2 = conn.end2_props

        self.end1_mult_combo.setCurrentText(str(e1.get("multiplicity", "")))
        self.end1_name_edit.setText(str(e1.get("name", "")))
        vis1 = str(e1.get("visibility", "public"))
        idx1 = self.end1_vis_combo.findText(vis1)
        if idx1 >= 0:
            self.end1_vis_combo.setCurrentIndex(idx1)

        self.end2_mult_combo.setCurrentText(str(e2.get("multiplicity", "")))
        self.end2_name_edit.setText(str(e2.get("name", "")))
        vis2 = str(e2.get("visibility", "public"))
        idx2 = self.end2_vis_combo.findText(vis2)
        if idx2 >= 0:
            self.end2_vis_combo.setCurrentIndex(idx2)

    def get_end1_props(self) -> Dict[str, str]:
        nav = "unspecified"
        if self.connection and "navigable" in self.connection.end1_props:
            nav = self.connection.end1_props["navigable"]
        return {
            "multiplicity": self.end1_mult_combo.currentText().strip(),
            "name": self.end1_name_edit.text().strip(),
            "visibility": self.end1_vis_combo.currentText().strip() or "public",
            "navigable": nav,
        }

    def get_end2_props(self) -> Dict[str, str]:
        nav = "unspecified"
        if self.connection and "navigable" in self.connection.end2_props:
            nav = self.connection.end2_props["navigable"]
        return {
            "multiplicity": self.end2_mult_combo.currentText().strip(),
            "name": self.end2_name_edit.text().strip(),
            "visibility": self.end2_vis_combo.currentText().strip() or "public",
            "navigable": nav,
        }

    def accept(self) -> None:
        if self.connection is not None:
            self.connection.end1_props.update(self.get_end1_props())
            self.connection.end2_props.update(self.get_end2_props())
            self.connection.prepareGeometryChange()
            self.connection.update()
        super().accept()


class DiagramConnectionItem(QGraphicsLineItem):
    """
    Representa uma linha de conexão UML com semântica visual completa:
    - Association: linha sólida sem pontas.
    - Directed Association: linha sólida com seta aberta (V invertido) no destino.
    - Aggregation: linha sólida com losango vazio na origem.
    - Composition: linha sólida com losango preenchido na origem.
    - Dependency: linha tracejada com seta aberta (V invertido) no destino.
    - Generalization: linha sólida com triângulo vazio no destino.
    - Realization / Interface Realization: linha tracejada com triângulo vazio no destino.
    - Association Class: linha tracejada conectando a classe associativa ao ponto médio.
    """

    DASHED_TYPES = {
        "Dependency",
        "Realization",
        "Interface Realization",
        "Template Binding",
        "Association Class",
    }

    VISIBILITY_SYMBOLS = {
        "public": "+",
        "private": "-",
        "protected": "#",
        "package": "~",
    }

    def __init__(
        self,
        source_node: Any,
        target_node: Any,
        connection_type: str = "Generalization",
        parent: Optional[QGraphicsItem] = None,
        end1_props: Optional[Dict[str, str]] = None,
        end2_props: Optional[Dict[str, str]] = None,
    ) -> None:
        if isinstance(connection_type, QGraphicsItem):
            parent = connection_type
            connection_type = "Generalization"

        super().__init__(parent)
        self.source_node = source_node
        self.target_node = target_node
        self.connection_type: str = connection_type or "Generalization"

        # 1. Estrutura de Dados das Extremidades (end1_props e end2_props)
        self.end1_props: Dict[str, str] = {
            "multiplicity": "",
            "name": "",
            "visibility": "public",
            "navigable": "unspecified",
        }
        self.end2_props: Dict[str, str] = {
            "multiplicity": "",
            "name": "",
            "visibility": "public",
            "navigable": "unspecified",
        }
        if end1_props:
            self.end1_props.update(end1_props)
        if end2_props:
            self.end2_props.update(end2_props)

        # Referências para suporte a Association Class no ponto médio e Waypoints
        self.waypoints: List[WaypointItem] = []
        self.anchor_item: Optional[AnchorItem] = None
        self.association_class_node: Optional[DiagramNodeItem] = None
        self.association_class_link: Optional[DiagramConnectionItem] = None

        if hasattr(self.source_node, "add_connection"):
            self.source_node.add_connection(self)
        if hasattr(self.target_node, "add_connection"):
            self.target_node.add_connection(self)

        self.setZValue(-1)  # Mantém a linha sempre atrás dos nós
        self.setFlags(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)

        self.arrow_size = 15.0  # Comprimento das pontas (setas, triângulos e losangos)
        self._configure_pen()
        self.update_position()

    def _is_dashed(self) -> bool:
        """Verifica se o tipo de conexão exige linha tracejada (DashLine)."""
        return self.connection_type in self.DASHED_TYPES

    def _configure_pen(self) -> QPen:
        """Configura e aplica a QPen de acordo com o connection_type e estado de seleção."""
        line_style = (
            Qt.PenStyle.DashLine if self._is_dashed() else Qt.PenStyle.SolidLine
        )
        if self.isSelected():
            color = QColor(26, 115, 232)
            width = 2.5
        else:
            color = QColor(70, 80, 95)
            width = 1.8

        pen = QPen(color, width, line_style, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        self.setPen(pen)
        return pen

    def set_connection_type(self, connection_type: str) -> None:
        """Atualiza o tipo semântico da conexão e redesenha o item."""
        self.connection_type = connection_type
        self._configure_pen()
        self.update_position()
        self.update()

    def detach(self) -> None:
        """Remove a referência desta conexão dos nós de origem, destino, waypoints e âncoras."""
        if hasattr(self.source_node, "connections") and self in self.source_node.connections:
            self.source_node.connections.remove(self)
        if hasattr(self.target_node, "connections") and self in self.target_node.connections:
            self.target_node.connections.remove(self)

        for wp in list(self.waypoints):
            wp.parent_connection = None
            if wp.scene():
                wp.scene().removeItem(wp)
            wp.setParentItem(None)
        self.waypoints.clear()

        if self.anchor_item is not None:
            anchor = self.anchor_item
            self.anchor_item = None
            anchor.remove_all_connections()
            if anchor.scene():
                anchor.scene().removeItem(anchor)

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
        self,
        segment: Union[QLineF, Tuple[QPointF, QPointF]],
        rect: QRectF,
    ) -> Optional[QPointF]:
        """Calcula o ponto onde o segmento intersecta as bordas do retângulo (sceneBoundingRect)."""
        if isinstance(segment, tuple):
            center_line = QLineF(segment[0], segment[1])
        else:
            center_line = segment

        if center_line.length() == 0:
            return None

        edges = [
            QLineF(rect.topLeft(), rect.topRight()),
            QLineF(rect.topRight(), rect.bottomRight()),
            QLineF(rect.bottomRight(), rect.bottomLeft()),
            QLineF(rect.bottomLeft(), rect.topLeft()),
        ]
        # 1. Tenta interseção estrita dentro do segmento (BoundedIntersection)
        for edge in edges:
            has_inter, pt = self.intersect(center_line, edge)
            if has_inter and pt is not None:
                return pt

        # 2. Fallback caso um waypoint esteja próximo/dentro do retângulo: projeta o raio na direção do segmento
        dx = center_line.dx()
        dy = center_line.dy()
        length = center_line.length()
        if length > 0:
            scale = (max(rect.width(), rect.height()) * 2.0 + length) / length
            extended_line = QLineF(
                center_line.p1(),
                QPointF(
                    center_line.p1().x() + dx * scale,
                    center_line.p1().y() + dy * scale,
                ),
            )
            for edge in edges:
                has_inter, pt = self.intersect(extended_line, edge)
                if has_inter and pt is not None:
                    return pt
        return None

    def _compute_border_points(self) -> Tuple[QPointF, QPointF]:
        """
        Calcula os pontos de interseção com o sceneBoundingRect() das classes:
        - Class1 (source_node) usa o segmento (centro_origem, points[1]).
        - Class2 (target_node) usa o segmento (points[-2], centro_destino).
        """
        source_rect = self.source_node.sceneBoundingRect()
        target_rect = self.target_node.sceneBoundingRect()

        centro_origem = source_rect.center()
        centro_destino = target_rect.center()

        raw_points: List[QPointF] = (
            [centro_origem]
            + [wp.pos() for wp in self.waypoints]
            + [centro_destino]
        )

        seg_origem = QLineF(centro_origem, raw_points[1])
        seg_destino = QLineF(raw_points[-2], centro_destino)

        if isinstance(self.source_node, AnchorItem) or seg_origem.length() == 0:
            ponto_origem_intersectado = centro_origem
        else:
            ponto_origem_intersectado = (
                self.get_rect_intersection(seg_origem, source_rect) or centro_origem
            )

        if isinstance(self.target_node, AnchorItem) or seg_destino.length() == 0:
            ponto_destino_intersectado = centro_destino
        else:
            ponto_destino_intersectado = (
                self.get_rect_intersection(seg_destino, target_rect) or centro_destino
            )

        return (
            self.mapFromScene(ponto_origem_intersectado),
            self.mapFromScene(ponto_destino_intersectado),
        )

    def get_polyline_points(self) -> List[QPointF]:
        """Retorna a sequência completa de pontos da Polyline: [origem] + waypoints + [destino]."""
        ponto_origem_intersectado, ponto_destino_intersectado = (
            self._compute_border_points()
        )
        return (
            [ponto_origem_intersectado]
            + [wp.pos() for wp in self.waypoints]
            + [ponto_destino_intersectado]
        )

    @staticmethod
    def _point_to_segment_distance(
        pt: QPointF, a: QPointF, b: QPointF
    ) -> Tuple[float, float]:
        """Retorna (distância do ponto ao segmento AB, projeção normalizada t em [0, 1])."""
        dx = b.x() - a.x()
        dy = b.y() - a.y()
        len_sq = dx * dx + dy * dy
        if len_sq == 0.0:
            return math.hypot(pt.x() - a.x(), pt.y() - a.y()), 0.0
        t = ((pt.x() - a.x()) * dx + (pt.y() - a.y()) * dy) / len_sq
        t_clamped = max(0.0, min(1.0, t))
        proj_x = a.x() + t_clamped * dx
        proj_y = a.y() + t_clamped * dy
        return math.hypot(pt.x() - proj_x, pt.y() - proj_y), t_clamped

    def add_waypoint(
        self, pos: QPointF, sort_by_projection: bool = True
    ) -> WaypointItem:
        """
        Instancia um WaypointItem na posição fornecida, insere na lista `self.waypoints`
        mantendo a ordem sequencial ao longo da linha e adiciona-o à cena.
        """
        wp = WaypointItem(pos.x(), pos.y(), parent_connection=self)
        if not self.waypoints or not sort_by_projection:
            self.waypoints.append(wp)
        else:
            pts = self.get_polyline_points()
            best_seg_idx = len(self.waypoints)
            best_dist = float("inf")
            for i in range(len(pts) - 1):
                dist, _ = self._point_to_segment_distance(pos, pts[i], pts[i + 1])
                if dist < best_dist:
                    best_dist = dist
                    best_seg_idx = i
            self.waypoints.insert(best_seg_idx, wp)

        if self.scene() is not None and wp.scene() != self.scene():
            self.scene().addItem(wp)

        self.update_position()
        self.update()
        return wp

    def mouseDoubleClickEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        """Cria um novo WaypointItem na posição do duplo clique sobre a linha."""
        if event is not None and event.button() == Qt.MouseButton.LeftButton:
            click_pos = event.scenePos()
            self.add_waypoint(click_pos, sort_by_projection=True)
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    def get_midpoint_scene(self) -> QPointF:
        """Retorna o ponto médio (midpoint) ao longo da Polyline em coordenadas da cena."""
        pts = self.get_polyline_points()
        if len(pts) < 2:
            return self.mapToScene(pts[0]) if pts else QPointF(0.0, 0.0)

        seg_lengths = [
            math.hypot(pts[i + 1].x() - pts[i].x(), pts[i + 1].y() - pts[i].y())
            for i in range(len(pts) - 1)
        ]
        total_len = sum(seg_lengths)
        if total_len == 0.0:
            return self.mapToScene(pts[0])

        half_len = total_len / 2.0
        accum = 0.0
        for i, seg_len in enumerate(seg_lengths):
            if accum + seg_len >= half_len and seg_len > 0:
                ratio = (half_len - accum) / seg_len
                mx = pts[i].x() + ratio * (pts[i + 1].x() - pts[i].x())
                my = pts[i].y() + ratio * (pts[i + 1].y() - pts[i].y())
                return self.mapToScene(QPointF(mx, my))
            accum += seg_len

        mid_local = QPointF(
            (pts[0].x() + pts[-1].x()) / 2.0, (pts[0].y() + pts[-1].y()) / 2.0
        )
        return self.mapToScene(mid_local)

    def _sync_anchor_position(self, p1: QPointF, p2: QPointF) -> None:
        """Mantém o nó de ancoragem sincronizado exatamente no ponto médio da Polyline."""
        if self.anchor_item is not None:
            mid_scene = self.get_midpoint_scene()
            self.anchor_item.setPos(mid_scene)
            for conn in list(self.anchor_item.connections):
                conn.update_position()

    def update_position(self) -> None:
        """Recalcula os pontos inicial e final da linha nas bordas (Bounding Box) dos nós."""
        if not self.source_node or not self.target_node:
            return

        self.prepareGeometryChange()
        p1, p2 = self._compute_border_points()
        self.setLine(QLineF(p1, p2))
        self._sync_anchor_position(p1, p2)

    def open_config_dialog(self) -> bool:
        """Abre a janela de diálogo ConnectionConfigDialog para editar end1_props e end2_props."""
        win = get_main_window(self)
        dialog = ConnectionConfigDialog(self, parent=win)
        if dialog.exec() == int(QDialog.DialogCode.Accepted):
            self.end1_props.update(dialog.get_end1_props())
            self.end2_props.update(dialog.get_end2_props())
            self.prepareGeometryChange()
            self.update()
            return True
        return False

    def ensure_anchor_item(self) -> AnchorItem:
        """Garante a existência de um AnchorItem no ponto médio desta conexão."""
        midpoint = self.get_midpoint_scene()
        if self.anchor_item is None:
            self.anchor_item = AnchorItem(
                midpoint.x(), midpoint.y(), parent_connection=self
            )
            if self.scene() and self.anchor_item.scene() != self.scene():
                self.scene().addItem(self.anchor_item)
        else:
            self.anchor_item.setPos(midpoint)
            if self.scene() and self.anchor_item.scene() != self.scene():
                self.scene().addItem(self.anchor_item)
        return self.anchor_item

    def add_association_class(
        self, assoc_node: Optional[DiagramNodeItem] = None
    ) -> Optional[DiagramNodeItem]:
        """
        Cria um nó de ancoragem no midpoint da linha, instancia um DiagramNodeItem
        chamado 'AssociationClass' e conecta-os com uma linha tracejada ('Association Class').
        """
        scene = self.scene()
        if scene is None:
            return None

        # a) Calcula o ponto médio (midpoint) da linha atual
        p1, p2 = self._compute_border_points()
        midpoint = self.mapToScene(
            QPointF((p1.x() + p2.x()) / 2.0, (p1.y() + p2.y()) / 2.0)
        )

        # b) Cria o nó de ancoragem nesse midpoint
        anchor = self.ensure_anchor_item()

        # c) Instancia automaticamente um novo DiagramNodeItem chamado "AssociationClass"
        if assoc_node is None:
            dx = p2.x() - p1.x()
            dy = p2.y() - p1.y()
            length = math.hypot(dx, dy) or 1.0
            nx = -dy / length
            ny = dx / length
            if ny < 0:
                nx, ny = -nx, -ny

            node_x = midpoint.x() + nx * 90.0 - 85.0
            node_y = midpoint.y() + ny * 90.0
            assoc_node = DiagramNodeItem(
                title="AssociationClass",
                x=node_x,
                y=node_y,
                width=170,
                height=110,
            )
            scene.addItem(assoc_node)

        # d) Cria o DiagramConnectionItem com connection_type="Association Class"
        assoc_conn = DiagramConnectionItem(
            assoc_node,
            anchor,
            connection_type="Association Class",
        )
        scene.addItem(assoc_conn)

        self.association_class_node = assoc_node
        self.association_class_link = assoc_conn
        self._sync_anchor_position(p1, p2)

        win = get_main_window(self)
        if win and hasattr(win, "update_tree"):
            win.update_tree()

        return assoc_node

    def contextMenuEvent(self, event: QGraphicsSceneContextMenuEvent) -> None:
        """Menu de contexto da conexão com opções de configuração e classe associativa."""
        menu = QMenu()
        action_config = menu.addAction("Configurar Ligação...")
        action_assoc_class = menu.addAction("Adicionar Classe Associativa")

        selected = menu.exec(event.screenPos())
        if selected == action_config:
            self.open_config_dialog()
        elif selected == action_assoc_class:
            self.add_association_class()

        event.accept()

    def draw_open_arrow(
        self, painter: QPainter, point_end: QPointF, angle_destino: float, solid_pen: QPen
    ) -> None:
        """Desenha Seta Aberta (V invertido) no destino usando translate(points[-1]) e rotate(angle_destino)."""
        s = self.arrow_size
        w = self.arrow_size * 0.55

        painter.save()
        painter.translate(point_end)
        painter.rotate(angle_destino)
        painter.setPen(solid_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)

        arrow_poly = QPolygonF([
            QPointF(-s, -w),
            QPointF(0.0, 0.0),
            QPointF(-s, w),
        ])
        painter.drawPolyline(arrow_poly)
        painter.restore()

    def draw_hollow_triangle(
        self, painter: QPainter, point_end: QPointF, angle_destino: float, solid_pen: QPen
    ) -> None:
        """Desenha Triângulo Vazio (fundo branco) no destino usando translate(points[-1]) e rotate(angle_destino)."""
        s = self.arrow_size
        w = self.arrow_size * 0.55

        painter.save()
        painter.translate(point_end)
        painter.rotate(angle_destino)
        painter.setPen(solid_pen)
        painter.setBrush(QBrush(QColor(255, 255, 255)))

        triangle_poly = QPolygonF([
            QPointF(0.0, 0.0),
            QPointF(-s, -w),
            QPointF(-s, w),
        ])
        painter.drawPolygon(triangle_poly)
        painter.restore()

    def draw_diamond(
        self,
        painter: QPainter,
        point_start: QPointF,
        angle_origem: float,
        solid_pen: QPen,
        filled: bool = False,
    ) -> None:
        """Desenha Losango Vazio (Aggregation) ou Preenchido (Composition) na origem usando translate(points[0]) e rotate(angle_origem)."""
        s = self.arrow_size * 0.75
        w = self.arrow_size * 0.45

        painter.save()
        painter.translate(point_start)
        painter.rotate(angle_origem)
        painter.setPen(solid_pen)
        if filled:
            painter.setBrush(QBrush(solid_pen.color()))
        else:
            painter.setBrush(QBrush(QColor(255, 255, 255)))

        diamond_poly = QPolygonF([
            QPointF(0.0, 0.0),
            QPointF(s, -w),
            QPointF(2.0 * s, 0.0),
            QPointF(s, w),
        ])
        painter.drawPolygon(diamond_poly)
        painter.restore()

    def _format_role_name(self, props: Dict[str, str]) -> str:
        """Formata o nome do papel (role name) com o símbolo de visibilidade correspondente."""
        raw_name = str(props.get("name", "")).strip()
        if not raw_name:
            return ""
        if raw_name[0] in ("+", "-", "#", "~"):
            return raw_name
        vis = str(props.get("visibility", "public")).strip().lower()
        symbol = self.VISIBILITY_SYMBOLS.get(vis, "+")
        return f"{symbol}{raw_name}"

    def _draw_endpoint_labels(
        self, painter: QPainter, points: List[QPointF]
    ) -> None:
        """
        Desenha a multiplicidade e o nome das extremidades (end1_props e end2_props)
        usando o primeiro e o último segmento da Polyline (~20px de offset).
        """
        if len(points) < 2:
            return

        painter.save()
        font = QFont("Segoe UI", 9)
        painter.setFont(font)
        painter.setPen(QPen(QColor(30, 41, 59)))
        fm = painter.fontMetrics()

        offset1 = 28.0 if self.connection_type in ("Aggregation", "Composition") else 22.0
        offset2 = (
            26.0
            if self.connection_type
            in (
                "Directed Association",
                "Dependency",
                "Generalization",
                "Realization",
                "Interface Realization",
            )
            else 22.0
        )
        perp_dist = 14.0

        # Extremidade 1 (Origem): usa o primeiro segmento (points[0] -> points[1])
        p1 = points[0]
        p1_next = points[1]
        dx1 = p1_next.x() - p1.x()
        dy1 = p1_next.y() - p1.y()
        len1 = math.hypot(dx1, dy1)
        if len1 > 0:
            ux1 = dx1 / len1
            uy1 = dy1 / len1
            nx1, ny1 = -uy1, ux1
            if ny1 > 0:
                nx1, ny1 = -nx1, -ny1

            base1 = QPointF(p1.x() + ux1 * offset1, p1.y() + uy1 * offset1)
            mult1 = str(self.end1_props.get("multiplicity", "")).strip()
            name1 = self._format_role_name(self.end1_props)

            if mult1:
                tw = fm.horizontalAdvance(mult1)
                th = fm.ascent()
                pos_m1 = QPointF(
                    base1.x() + nx1 * perp_dist - tw / 2.0,
                    base1.y() + ny1 * perp_dist + th / 2.0,
                )
                painter.drawText(pos_m1, mult1)

            if name1:
                tw = fm.horizontalAdvance(name1)
                th = fm.ascent()
                pos_n1 = QPointF(
                    base1.x() - nx1 * perp_dist - tw / 2.0,
                    base1.y() - ny1 * perp_dist + th / 2.0,
                )
                painter.drawText(pos_n1, name1)

        # Extremidade 2 (Destino): usa o último segmento (points[-2] -> points[-1])
        p2_prev = points[-2]
        p2 = points[-1]
        dx2 = p2.x() - p2_prev.x()
        dy2 = p2.y() - p2_prev.y()
        len2 = math.hypot(dx2, dy2)
        if len2 > 0:
            ux2 = dx2 / len2
            uy2 = dy2 / len2
            nx2, ny2 = -uy2, ux2
            if ny2 > 0:
                nx2, ny2 = -nx2, -ny2

            base2 = QPointF(p2.x() - ux2 * offset2, p2.y() - uy2 * offset2)
            mult2 = str(self.end2_props.get("multiplicity", "")).strip()
            name2 = self._format_role_name(self.end2_props)

            if mult2:
                tw = fm.horizontalAdvance(mult2)
                th = fm.ascent()
                pos_m2 = QPointF(
                    base2.x() + nx2 * perp_dist - tw / 2.0,
                    base2.y() + ny2 * perp_dist + th / 2.0,
                )
                painter.drawText(pos_m2, mult2)

            if name2:
                tw = fm.horizontalAdvance(name2)
                th = fm.ascent()
                pos_n2 = QPointF(
                    base2.x() - nx2 * perp_dist - tw / 2.0,
                    base2.y() - ny2 * perp_dist + th / 2.0,
                )
                painter.drawText(pos_n2, name2)

        painter.restore()

    def boundingRect(self) -> QRectF:
        """Expande os limites englobando todos os waypoints, pontas e textos."""
        extra = self.pen().widthF() + self.arrow_size * 2.0 + 60.0
        if self.source_node and self.target_node:
            pts = self.get_polyline_points()
            if pts:
                poly_rect = QPolygonF(pts).boundingRect()
                return poly_rect.normalized().adjusted(-extra, -extra, extra, extra)
        return (
            QRectF(self.line().p1(), self.line().p2())
            .normalized()
            .adjusted(-extra, -extra, extra, extra)
        )

    def shape(self) -> QPainterPath:
        """Define uma área de clique confortável ao longo de toda a Polyline."""
        if self.source_node and self.target_node:
            pts = self.get_polyline_points()
            if len(pts) >= 2:
                base_path = QPainterPath()
                base_path.moveTo(pts[0])
                for pt in pts[1:]:
                    base_path.lineTo(pt)
                stroker = QPainterPathStroker()
                stroker.setWidth(14.0)
                path = stroker.createStroke(base_path)
                r = self.arrow_size
                path.addEllipse(pts[0], r, r)
                path.addEllipse(pts[-1], r, r)
                return path
        return super().shape()

    def paint(self, painter: QPainter, option: Any, widget: Optional[QWidget] = None) -> None:
        """Renderiza a Polyline de ligação, extremidades UML e textos (multiplicidade/nomes)."""
        if (
            not self.source_node
            or not self.target_node
            or self.source_node.scene() != self.scene()
            or self.target_node.scene() != self.scene()
        ):
            return

        # 1 & 4. Obtém os pontos de interseção e constrói a lista completa de pontos da conexão
        ponto_origem_intersectado, ponto_destino_intersectado = (
            self._compute_border_points()
        )
        points: List[QPointF] = (
            [ponto_origem_intersectado]
            + [wp.pos() for wp in self.waypoints]
            + [ponto_destino_intersectado]
        )
        if len(points) < 2:
            return

        # 2. Correção Trigonométrica para as Pontas (CRÍTICO):
        # Ângulo da ORIGEM (End 1) calculado APENAS entre points[0] e points[1]
        dy_origem = points[1].y() - points[0].y()
        dx_origem = points[1].x() - points[0].x()
        if math.hypot(dx_origem, dy_origem) == 0 and len(points) == 2:
            return
        angle_origem = math.degrees(math.atan2(dy_origem, dx_origem))

        # Ângulo do DESTINO (End 2) calculado APENAS entre points[-2] e points[-1]
        dy_destino = points[-1].y() - points[-2].y()
        dx_destino = points[-1].x() - points[-2].x()
        angle_destino = math.degrees(math.atan2(dy_destino, dx_destino))

        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        # Configura o estilo da linha conforme o tipo de conexão UML
        if self.connection_type in (
            "Dependency",
            "Realization",
            "Interface Realization",
            "Template Binding",
            "Association Class",
        ):
            line_style = Qt.PenStyle.DashLine
        else:
            line_style = Qt.PenStyle.SolidLine

        color = QColor(26, 115, 232) if self.isSelected() else QColor(70, 80, 95)
        width = 2.5 if self.isSelected() else 1.8

        pen = QPen(color, width, line_style, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)

        # Desenha PRIMEIRO a linha principal (Polyline)
        painter.drawPolyline(QPolygonF(points))

        # 3. Isolamento e Renderização das pontas com painter.save() / painter.restore()
        solid_pen = QPen(color, width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)

        if self.connection_type in ("Directed Association", "Dependency", "Template Binding"):
            self.draw_open_arrow(painter, points[-1], angle_destino, solid_pen)
        elif self.connection_type in ("Generalization", "Realization", "Interface Realization"):
            self.draw_hollow_triangle(painter, points[-1], angle_destino, solid_pen)
        elif self.connection_type == "Aggregation":
            self.draw_diamond(painter, points[0], angle_origem, solid_pen, filled=False)
        elif self.connection_type == "Composition":
            self.draw_diamond(painter, points[0], angle_origem, solid_pen, filled=True)

        # Renderiza multiplicidades e nomes nas extremidades 1 e 2
        self._draw_endpoint_labels(painter, points)


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
