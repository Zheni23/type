import sys
import signal
from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QVBoxLayout, QPushButton,
    QColorDialog, QSlider, QHBoxLayout, QGraphicsDropShadowEffect
)
from PyQt6.QtGui import QFont, QColor, QKeyEvent, QPainter, QPen, QMouseEvent, QAction
from PyQt6.QtCore import Qt, QPoint, pyqtSignal, QEvent, QTimer

# --- 1. THE FLOATING TEXT WIDGET ---
class FloatingText(QWidget):
    activated = pyqtSignal(object)

    def __init__(self, manager_ref, start_pos):
        super().__init__()
        self.manager = manager_ref
        
        # Window properties
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.WindowStaysOnTopHint | 
            Qt.WindowType.Tool 
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Data
        self.text_content = "Type..."
        self._font_size = 42
        self._color = QColor("#FFFFFF")
        self._shadow_enabled = True
        self.is_selected = True

        # UI
        self.label = QLabel(self)
        # CRITICAL FIX: This line ensures clicks pass through the text letters 
        # to the window below, guaranteeing dragging always works.
        self.label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        
        self.move(start_pos)
        self.show()

        # Dragging state
        self._dragging = False
        self._drag_offset = QPoint()

        # Cursor Blinking
        self.show_cursor = True
        self.cursor_timer = QTimer(self)
        self.cursor_timer.timeout.connect(self._blink_cursor)
        self.cursor_timer.start(500) 

        self.update_appearance()

    def _blink_cursor(self):
        if self.is_selected:
            self.show_cursor = not self.show_cursor
            self.update_appearance()

    def update_appearance(self):
        # 1. Update Font
        font = QFont("Arial", self._font_size)
        font.setBold(True)
        self.label.setFont(font)

        # 2. Prepare Text
        safe_text = self.text_content.replace("\n", "<br>")
        
        # Determine Color
        if not safe_text or self.text_content == "Type...":
            display_text = "Type..."
            c = QColor(self._color)
            c.setAlpha(150) 
            col_str = c.name(QColor.NameFormat.HexArgb)
        else:
            display_text = safe_text
            col_str = self._color.name()

        # 3. Add Visual Cursor if selected
        if self.is_selected and self.show_cursor:
            display_text += "|"

        # 4. Render HTML
        self.label.setText(f"<span style='color:{col_str};'>{display_text}</span>")
        self.label.adjustSize()
        
        # 5. Update Shadow
        if self._shadow_enabled:
            shadow = QGraphicsDropShadowEffect(self)
            shadow.setBlurRadius(15)
            shadow.setOffset(10, 10)
            shadow.setColor(QColor(0, 0, 0, 255))
            self.label.setGraphicsEffect(shadow)
        else:
            self.label.setGraphicsEffect(None)

        # 6. Resize window to fit label
        self.resize(self.label.width() + 20, self.label.height() + 20)
        self.label.move(10, 10)
        self.update() 

    def paintEvent(self, event):
        if self.is_selected:
            painter = QPainter(self)
            pen = QPen(QColor(0, 120, 255))
            pen.setWidth(2)
            pen.setStyle(Qt.PenStyle.DashLine)
            painter.setPen(pen)
            painter.drawRect(2, 2, self.width()-4, self.height()-4)

    # --- DRAGGING LOGIC ---
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.activated.emit(self) 
            self._dragging = True
            # Capture where we clicked relative to the window top-left
            self._drag_offset = event.pos()

    def mouseMoveEvent(self, event):
        if self._dragging:
            # Calculate new position based on global mouse pos minus the offset
            self.move(event.globalPosition().toPoint() - self._drag_offset)

    def mouseReleaseEvent(self, event):
        self._dragging = False

# --- 2. THE CONTROL BAR ---
class ControlBar(QWidget):
    def __init__(self):
        super().__init__()
        self.active_text_widget = None
        self.text_widgets = []
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Text Tools")
        self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint)
        self.setGeometry(100, 100, 420, 60)
        self.setStyleSheet("background-color: #222; color: #eee;")

        layout = QHBoxLayout()

        self.btn_add = QPushButton("+ Text")
        self.btn_add.clicked.connect(self.create_text_widget)
        self.btn_add.setStyleSheet("background-color: #0078d7; font-weight: bold; border-radius: 4px;")

        self.slider_size = QSlider(Qt.Orientation.Horizontal)
        self.slider_size.setRange(10, 200)
        self.slider_size.setValue(42)
        self.slider_size.setFixedWidth(100)
        self.slider_size.valueChanged.connect(self.on_size_change)

        self.btn_color = QPushButton("Color")
        self.btn_color.clicked.connect(self.on_color_click)
        self.btn_color.setStyleSheet("background-color: #444; border-radius: 4px;")

        self.btn_shadow = QPushButton("Shadow")
        self.btn_shadow.setCheckable(True)
        self.btn_shadow.setChecked(True)
        self.btn_shadow.clicked.connect(self.on_shadow_toggle)
        self.btn_shadow.setStyleSheet("background-color: #444; border-radius: 4px;")

        self.btn_del = QPushButton("✕")
        self.btn_del.clicked.connect(self.delete_current)
        self.btn_del.setFixedWidth(30)
        self.btn_del.setStyleSheet("background-color: #c42b1c; border-radius: 4px;")

        layout.addWidget(self.btn_add)
        layout.addWidget(QLabel("Size:"))
        layout.addWidget(self.slider_size)
        layout.addWidget(self.btn_color)
        layout.addWidget(self.btn_shadow)
        layout.addWidget(self.btn_del)
        
        self.setLayout(layout)
        self.show()

    def create_text_widget(self):
        pos = self.geometry().bottomLeft() + QPoint(20, 20)
        new_widget = FloatingText(self, pos)
        new_widget.activated.connect(self.set_active_widget)
        self.text_widgets.append(new_widget)
        self.set_active_widget(new_widget)

    def set_active_widget(self, widget):
        for w in self.text_widgets:
            w.is_selected = False
            w.update_appearance() 

        self.active_text_widget = widget
        if widget:
            widget.is_selected = True
            widget.raise_() 
            widget.update_appearance() 
            
            self.slider_size.blockSignals(True)
            self.slider_size.setValue(widget._font_size)
            self.slider_size.blockSignals(False)
            
            self.btn_shadow.blockSignals(True)
            self.btn_shadow.setChecked(widget._shadow_enabled)
            self.btn_shadow.blockSignals(False)

    def delete_current(self):
        if self.active_text_widget:
            self.active_text_widget.close()
            self.text_widgets.remove(self.active_text_widget)
            self.active_text_widget = None

    def on_size_change(self, val):
        if self.active_text_widget:
            self.active_text_widget._font_size = val
            self.active_text_widget.update_appearance()

    def on_color_click(self):
        if self.active_text_widget:
            col = QColorDialog.getColor(self.active_text_widget._color, self)
            if col.isValid():
                self.active_text_widget._color = col
                self.active_text_widget.update_appearance()

    def on_shadow_toggle(self):
        if self.active_text_widget:
            self.active_text_widget._shadow_enabled = self.btn_shadow.isChecked()
            self.active_text_widget.update_appearance()

# --- 3. CUSTOM APP TO HANDLE GLOBAL KEYS ---
class MyApplication(QApplication):
    def __init__(self, argv):
        super().__init__(argv)
        self.control_bar = None

    def notify(self, receiver, event):
        if (event.type() == QEvent.Type.KeyPress and 
            self.control_bar and 
            self.control_bar.active_text_widget):
            
            key = event.key()
            txt_widget = self.control_bar.active_text_widget
            current_str = txt_widget.text_content
            
            # 1. MOVEMENT (Arrow Keys)
            if key == Qt.Key.Key_Up:    txt_widget.move(txt_widget.pos() + QPoint(0, -2))
            elif key == Qt.Key.Key_Down:  txt_widget.move(txt_widget.pos() + QPoint(0, 2))
            elif key == Qt.Key.Key_Left:  txt_widget.move(txt_widget.pos() + QPoint(-2, 0))
            elif key == Qt.Key.Key_Right: txt_widget.move(txt_widget.pos() + QPoint(2, 0))
            
            # 2. DESELECT
            elif key == Qt.Key.Key_Escape:
                self.control_bar.set_active_widget(None)
                
            # 3. TYPING
            elif key == Qt.Key.Key_Backspace:
                if current_str == "Type...": current_str = ""
                else: current_str = current_str[:-1]
                txt_widget.text_content = current_str
                txt_widget.update_appearance()
                
            elif key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                # If Shift is pressed -> Add new line
                if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                    txt_widget.text_content += "\n"
                    txt_widget.update_appearance()
                else:
                    # If just Enter -> Finish editing (Deselect)
                    self.control_bar.set_active_widget(None)
                 
            elif event.text() and event.text().isprintable():
                if current_str == "Type...": current_str = ""
                # Prevent control characters from printing
                if not (event.modifiers() & Qt.KeyboardModifier.ControlModifier):
                    txt_widget.text_content = current_str + event.text()
                    txt_widget.update_appearance()

            # Prevent buttons from triggering if we are typing
            if isinstance(receiver, QPushButton):
                 return super().notify(receiver, event)
                 
            return True # Consume event
            
        return super().notify(receiver, event)

def main():
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    app = MyApplication(sys.argv)
    bar = ControlBar()
    app.control_bar = bar 
    sys.exit(app.exec())

if __name__ == "__main__":
    main()