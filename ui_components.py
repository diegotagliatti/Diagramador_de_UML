"""
Módulo de Componentes de Interface Gráfica (ui_components.py)
Contém o Canvas (DiagramScene), o Visualizador Principal Otimizado (DiagramView)
e o Navegador de Visão Geral (MinimapView) do PyDiagram.
"""

from __future__ import annotations
from typing import Any, List, Optional

from PyQt6.QtCore import QLineF, QPointF, QRectF, Qt, pyqtSignal
from PyQt6.QtGui import (
    QBrush,
    QColor,
    QPainter,
    QPen,
)
from PyQt6.QtWidgets import (
    QGraphicsItem,
    QGraphicsLineItem,
    QGraphicsScene,
    QGraphicsSceneMouseEvent,
    QGraphicsView,
    QMenu,
    QWidget,
)

from uml_items import DiagramConnectionItem, DiagramNodeItem


class DiagramScene(QGraphicsScene):
    """Cena com grade quadriculada suave e suporte a conexões interativas por arrasto."""

    connection_mode_changed = pyqtSignal(bool)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setSceneRect(-2500, -2500, 5000, 5000)
        self.grid_size: int = 24

        # Estado do modo de conexão
        self._connection_mode: bool = False
        self.start_node: Optional[DiagramNodeItem] = None
        self.temp_connection_line: Optional[QGraphicsLineItem] = None

    @property
    def connection_mode(self) -> bool:
        return self._connection_mode

    @connection_mode.setter
    def connection_mode(self, value: bool) -> None:
        self.set_connection_mode(value)

    def set_connection_mode(self, enabled: bool) -> None:
        """Ativa ou desativa o modo de conexão entre classes."""
        if self._connection_mode != enabled:
            self._connection_mode = enabled
            if not enabled:
                self._clear_temp_connection()
                self.start_node = None

            for view in self.views():
                if enabled:
                    view.setCursor(Qt.CursorShape.CrossCursor)
                else:
                    view.unsetCursor()

            self.connection_mode_changed.emit(self._connection_mode)

    def scene(self) -> "DiagramScene":
        """Compatibilidade para chamadas no formato self.scene()."""
        return self

    def _clear_temp_connection(self) -> None:
        """Remove a linha temporária da cena com segurança."""
        if self.temp_connection_line:
            if self.temp_connection_line.scene():
                self.scene().removeItem(self.temp_connection_line)
            self.temp_connection_line.setParentItem(None)
            self.temp_connection_line = None

    def _resolve_node(self, item: Optional[QGraphicsItem]) -> Optional[DiagramNodeItem]:
        """Obtém a instância raiz de DiagramNodeItem caso o item clicado seja ela ou um filho."""
        curr = item
        while curr:
            if isinstance(curr, DiagramNodeItem):
                return curr
            curr = curr.parentItem()
        return None

    def drawBackground(self, painter: QPainter, rect: QRectF) -> None:
        """Desenha uma tela de fundo estilo StarUML com malha de pontos."""
        painter.fillRect(rect, QColor(248, 250, 252))

        left = int(rect.left()) - (int(rect.left()) % self.grid_size)
        top = int(rect.top()) - (int(rect.top()) % self.grid_size)

        pen = QPen(QColor(203, 213, 225), 1.5)
        painter.setPen(pen)

        points = []
        for x in range(left, int(rect.right()), self.grid_size):
            for y in range(top, int(rect.bottom()), self.grid_size):
                points.append(QPointF(x, y))
        painter.drawPoints(points)

    def mousePressEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        """Inicia linha de conexão temporária quando no modo de conexão."""
        if self._connection_mode and event.button() == Qt.MouseButton.LeftButton:
            target_node: Optional[DiagramNodeItem] = None
            for item in self.items(event.scenePos()):
                node = self._resolve_node(item)
                if node:
                    target_node = node
                    break

            if target_node:
                self.start_node = target_node
                center = target_node.sceneBoundingRect().center()
                self.temp_connection_line = QGraphicsLineItem(QLineF(center, event.scenePos()))
                pen = QPen(QColor(59, 130, 246), 2, Qt.PenStyle.DashLine)
                self.temp_connection_line.setPen(pen)
                self.temp_connection_line.setZValue(100)
                self.addItem(self.temp_connection_line)

                event.accept()
                return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        """Atualiza a coordenada final da linha temporária conforme o cursor move."""
        if self.temp_connection_line and self.start_node:
            line = self.temp_connection_line.line()
            line.setP2(event.scenePos())
            self.temp_connection_line.setLine(line)
            event.accept()
            return

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        """Finaliza a conexão temporária, conectando nós se solto sobre outro nó."""
        if self.temp_connection_line:
            self._clear_temp_connection()

            target_node: Optional[DiagramNodeItem] = None
            for item in self.items(event.scenePos()):
                node = self._resolve_node(item)
                if node and node != self.start_node:
                    target_node = node
                    break

            if self.start_node and target_node and target_node != self.start_node:
                win = self.parent()
                already_connected = any(
                    (c.source_node == self.start_node and c.target_node == target_node)
                    or (c.source_node == target_node and c.target_node == self.start_node)
                    for c in self.start_node.connections
                )
                if not already_connected:
                    connection = DiagramConnectionItem(self.start_node, target_node)
                    self.addItem(connection)
                    if win and hasattr(win, "statusbar") and hasattr(win, "i18n"):
                        win.statusbar.showMessage(
                            win.i18n.t("status_nodes_connected", "Nós conectados com sucesso."),
                            3000,
                        )
                else:
                    if win and hasattr(win, "statusbar"):
                        win.statusbar.showMessage("Esses nós já estão conectados.", 3000)

                self.connection_mode = False

            self.start_node = None
            event.accept()
            return

        super().mouseReleaseEvent(event)


class DiagramView(QGraphicsView):
    """
    Visualizador otimizado com renderização de alto desempenho,
    suporte a zoom por roda do mouse, navegação por arrasto (pan) e rubber band selection.
    """

    def __init__(self, scene: QGraphicsScene, parent: Optional[QWidget] = None) -> None:
        super().__init__(scene, parent)
        self.minimap_view: Optional[MinimapView] = None

        # Otimizações de desempenho estritas
        self.setRenderHints(
            QPainter.RenderHint.Antialiasing
            | QPainter.RenderHint.TextAntialiasing
            | QPainter.RenderHint.SmoothPixmapTransform
        )
        self.setOptimizationFlag(QGraphicsView.OptimizationFlag.DontSavePainterState, True)
        self.setOptimizationFlag(QGraphicsView.OptimizationFlag.DontAdjustForAntialiasing, True)
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.SmartViewportUpdate)

        self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        # Sincroniza minimapa com scroll
        self.horizontalScrollBar().valueChanged.connect(self._on_scroll_changed)
        self.verticalScrollBar().valueChanged.connect(self._on_scroll_changed)

    def _on_scroll_changed(self, *args: Any) -> None:
        if self.minimap_view:
            self.minimap_view.viewport().update()

    def mousePressEvent(self, event: Any) -> None:
        # Panning manual: Ctrl + Botão Esquerdo
        if (
            event.button() == Qt.MouseButton.LeftButton
            and (event.modifiers() & Qt.KeyboardModifier.ControlModifier)
        ):
            self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
            super().mousePressEvent(event)
            return

        if getattr(self.scene(), "connection_mode", False):
            old_drag = self.dragMode()
            self.setDragMode(QGraphicsView.DragMode.NoDrag)
            super().mousePressEvent(event)
            self.setDragMode(old_drag)
            return

        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event: Any) -> None:
        super().mouseReleaseEvent(event)
        if self.dragMode() == QGraphicsView.DragMode.ScrollHandDrag:
            self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)

    def wheelEvent(self, event: Any) -> None:
        """Zoom interativo centrado no cursor."""
        zoom_in_factor = 1.15
        zoom_out_factor = 1.0 / zoom_in_factor

        if event.angleDelta().y() > 0:
            self.scale(zoom_in_factor, zoom_in_factor)
        else:
            self.scale(zoom_out_factor, zoom_out_factor)

        if self.minimap_view:
            self.minimap_view.viewport().update()

    def resizeEvent(self, event: Any) -> None:
        super().resizeEvent(event)
        if self.minimap_view:
            self.minimap_view.update_minimap()

    def contextMenuEvent(self, event: Any) -> None:
        """Menu de contexto na área vazia do canvas."""
        if self.itemAt(event.pos()) is None:
            scene_pos = self.mapToScene(event.pos())
            menu = QMenu(self)
            action_new_class = menu.addAction("Nova Classe")
            action_new_class.triggered.connect(lambda: self.create_node_at(scene_pos))
            menu.exec(event.globalPos())
            event.accept()
        else:
            super().contextMenuEvent(event)

    def create_node_at(self, scene_pos: QPointF, title: str = "NovaClasse") -> DiagramNodeItem:
        """Cria e insere nó UML na posição clicada."""
        win = self.window()
        if win and hasattr(win, "create_class_at"):
            return win.create_class_at(scene_pos, title=title)

        node = DiagramNodeItem(title=title, width=160, height=100)
        node.setPos(scene_pos)
        self.scene().addItem(node)
        self.scene().clearSelection()
        node.setSelected(True)
        return node


class MinimapView(QGraphicsView):
    """
    Minimapa para visão global do diagrama:
    - Otimizado com SmartViewportUpdate e flags DontSavePainterState/DontAdjustForAntialiasing.
    - Exibe a área do viewport principal em tempo real no drawForeground.
    """

    def __init__(
        self,
        scene: QGraphicsScene,
        main_view: Optional[DiagramView] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(scene, parent)
        self.main_view = main_view

        self.setRenderHints(
            QPainter.RenderHint.Antialiasing
            | QPainter.RenderHint.SmoothPixmapTransform
        )
        self.setOptimizationFlag(QGraphicsView.OptimizationFlag.DontSavePainterState, True)
        self.setOptimizationFlag(QGraphicsView.OptimizationFlag.DontAdjustForAntialiasing, True)
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.SmartViewportUpdate)

        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setInteractive(False)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setStyleSheet(
            "background-color: #f8fafc; border: 1px solid #cbd5e1; border-radius: 4px;"
        )

    def update_minimap(self) -> None:
        """Ajusta o enquadramento do minimapa para exibir toda a extensão dos nós."""
        if not self.scene():
            return
        rect = self.scene().itemsBoundingRect()
        if rect.isEmpty():
            rect = QRectF(-400, -300, 800, 600)
        else:
            rect = rect.adjusted(-120, -120, 120, 120)
        self.fitInView(rect, Qt.AspectRatioMode.KeepAspectRatio)
        self.viewport().update()

    def resizeEvent(self, event: Any) -> None:
        super().resizeEvent(event)
        self.update_minimap()

    def drawForeground(self, painter: QPainter, rect: QRectF) -> None:
        """Desenha o retângulo translúcido indicando a região visível da view principal."""
        super().drawForeground(painter, rect)
        if not self.main_view:
            return

        visible_scene_poly = self.main_view.mapToScene(
            self.main_view.viewport().rect()
        )
        visible_rect = visible_scene_poly.boundingRect()

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(QColor(37, 99, 235, 220), 1.5, Qt.PenStyle.SolidLine)
        brush = QBrush(QColor(59, 130, 246, 50))
        painter.setPen(pen)
        painter.setBrush(brush)
        painter.drawRect(visible_rect)
        painter.restore()
