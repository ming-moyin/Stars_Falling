"""
渗透测试工具调用框架
类似 Dawn Launcher 风格的工具管理器
"""
import sys
import json
import subprocess
import os
import ctypes
from pathlib import Path
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QListWidget, QListWidgetItem, QPushButton, QLineEdit, QLabel,
    QTextEdit, QCheckBox, QDialog, QFormLayout, QComboBox,
    QMessageBox, QSplitter, QFrame, QScrollArea, QGridLayout,
    QMenu, QAction, QInputDialog, QGroupBox, QTabWidget, QSizePolicy
)
from PyQt5.QtCore import Qt, QSize, QMimeData, pyqtSignal
from PyQt5.QtGui import QFont, QIcon, QColor, QPalette, QDrag, QPixmap


CONFIG_FILE = "tools_config.json"

def resource_path(relative_path):
    """获取资源文件路径，支持打包后的exe"""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)


class AddToolDialog(QDialog):
    """添加/编辑工具对话框"""
    def __init__(self, parent=None, categories=None, tool_data=None):
        super().__init__(parent)
        self.categories = categories or ["默认"]
        self.tool_data = tool_data
        # 去掉问号图标
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.init_ui()
        # 设置深色标题栏
        self.set_dark_titlebar()

    def set_dark_titlebar(self):
        """Windows深色标题栏"""
        if sys.platform == 'win32':
            try:
                hwnd = int(self.winId())
                DWMWA_USE_IMMERSIVE_DARK_MODE = 20
                DWMWA_CAPTION_COLOR = 35
                ctypes.windll.dwmapi.DwmSetWindowAttribute(
                    hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE,
                    ctypes.byref(ctypes.c_int(1)), ctypes.sizeof(ctypes.c_int)
                )
                color = 0x002e1e1e  # BGR: #1e1e2e
                ctypes.windll.dwmapi.DwmSetWindowAttribute(
                    hwnd, DWMWA_CAPTION_COLOR,
                    ctypes.byref(ctypes.c_int(color)), ctypes.sizeof(ctypes.c_int)
                )
            except:
                pass

    def init_ui(self):
        self.setWindowTitle("添加工具" if not self.tool_data else "编辑工具")
        self.setMinimumWidth(500)
        self.setStyleSheet("""
            QDialog {
                background-color: #1e1e2e;
            }
            QLabel {
                color: #cdd6f4;
                font-size: 18px;
            }
            QLineEdit, QComboBox, QTextEdit {
                background-color: #313244;
                color: #cdd6f4;
                border: 1px solid #45475a;
                border-radius: 5px;
                padding: 10px;
                font-size: 18px;
            }
            QLineEdit:focus, QTextEdit:focus {
                border: 1px solid #89b4fa;
            }
            QPushButton {
                background-color: #89b4fa;
                color: #1e1e2e;
                border: none;
                border-radius: 5px;
                padding: 12px 24px;
                font-size: 18px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #b4befe;
            }
            QPushButton#cancelBtn {
                background-color: #45475a;
                color: #cdd6f4;
            }
        """)

        layout = QFormLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # 工具名称
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("例如: Nmap")
        layout.addRow("工具名称:", self.name_edit)

        # 分类
        self.category_combo = QComboBox()
        self.category_combo.addItems(self.categories)
        self.category_combo.setEditable(True)
        layout.addRow("分类:", self.category_combo)

        # 路径（工具可执行文件路径）
        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText("工具可执行文件路径")
        layout.addRow("路径:", self.path_edit)

        # 参数
        self.command_edit = QTextEdit()
        self.command_edit.setPlaceholderText("参数，使用 {url} 作为目标占位符")
        self.command_edit.setMaximumHeight(100)
        layout.addRow("参数:", self.command_edit)

        # 起始位置（工作目录）
        self.startdir_edit = QLineEdit()
        self.startdir_edit.setPlaceholderText("工具执行的起始目录")
        layout.addRow("起始位置:", self.startdir_edit)

        # 描述
        self.desc_edit = QLineEdit()
        self.desc_edit.setPlaceholderText("工具描述")
        layout.addRow("描述:", self.desc_edit)

        # 按钮
        btn_layout = QHBoxLayout()
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.setObjectName("cancelBtn")
        self.cancel_btn.clicked.connect(self.reject)
        
        self.save_btn = QPushButton("保存")
        self.save_btn.clicked.connect(self.accept)
        
        btn_layout.addWidget(self.cancel_btn)
        btn_layout.addWidget(self.save_btn)
        layout.addRow(btn_layout)

        # 如果是编辑模式，填充数据
        if self.tool_data:
            self.name_edit.setText(self.tool_data.get("name", ""))
            self.category_combo.setCurrentText(self.tool_data.get("category", "默认"))
            self.path_edit.setText(self.tool_data.get("path", ""))
            self.command_edit.setText(self.tool_data.get("command", ""))
            self.startdir_edit.setText(self.tool_data.get("startdir", "") or self.tool_data.get("workdir", ""))
            self.desc_edit.setText(self.tool_data.get("description", ""))

    def get_tool_data(self):
        return {
            "name": self.name_edit.text().strip(),
            "category": self.category_combo.currentText().strip(),
            "path": self.path_edit.text().strip(),
            "command": self.command_edit.toPlainText().strip(),
            "startdir": self.startdir_edit.text().strip(),
            "description": self.desc_edit.text().strip()
        }


class DarkInputDialog(QDialog):
    """深色主题输入对话框"""
    def __init__(self, parent=None, title="", label="", text="", items=None):
        super().__init__(parent)
        self.items = items
        self.result_text = ""
        # 去掉问号图标
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.init_ui(title, label, text)
        self.set_dark_titlebar()

    def set_dark_titlebar(self):
        """Windows深色标题栏"""
        if sys.platform == 'win32':
            try:
                hwnd = int(self.winId())
                DWMWA_USE_IMMERSIVE_DARK_MODE = 20
                DWMWA_CAPTION_COLOR = 35
                ctypes.windll.dwmapi.DwmSetWindowAttribute(
                    hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE,
                    ctypes.byref(ctypes.c_int(1)), ctypes.sizeof(ctypes.c_int)
                )
                color = 0x002e1e1e  # BGR: #1e1e2e
                ctypes.windll.dwmapi.DwmSetWindowAttribute(
                    hwnd, DWMWA_CAPTION_COLOR,
                    ctypes.byref(ctypes.c_int(color)), ctypes.sizeof(ctypes.c_int)
                )
            except:
                pass

    def init_ui(self, title, label, text):
        self.setWindowTitle(title)
        self.setMinimumWidth(350)
        self.setStyleSheet("""
            QDialog {
                background-color: #1e1e2e;
            }
            QLabel {
                color: #cdd6f4;
                font-size: 16px;
            }
            QLineEdit, QComboBox {
                background-color: #313244;
                color: #cdd6f4;
                border: 1px solid #45475a;
                border-radius: 5px;
                padding: 10px;
                font-size: 16px;
            }
            QPushButton {
                background-color: #89b4fa;
                color: #1e1e2e;
                border: none;
                border-radius: 5px;
                padding: 10px 20px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #b4befe;
            }
            QPushButton#cancelBtn {
                background-color: #45475a;
                color: #cdd6f4;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # 标签
        lbl = QLabel(label)
        layout.addWidget(lbl)

        # 输入框或下拉框
        if self.items:
            self.input = QComboBox()
            self.input.addItems(self.items)
        else:
            self.input = QLineEdit()
            self.input.setText(text)
        layout.addWidget(self.input)

        # 按钮
        btn_layout = QHBoxLayout()
        cancel_btn = QPushButton("取消")
        cancel_btn.setObjectName("cancelBtn")
        cancel_btn.clicked.connect(self.reject)
        
        ok_btn = QPushButton("确定")
        ok_btn.clicked.connect(self.accept)
        
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(ok_btn)
        layout.addLayout(btn_layout)

    def get_text(self):
        if self.items:
            return self.input.currentText()
        return self.input.text()


class SubCategoryHeader(QFrame):
    """子分类标题组件"""
    drag_started = pyqtSignal(object)  # 拖拽开始信号
    
    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.title = title
        self._drag_start_pos = None
        self.init_ui()
    
    def init_ui(self):
        self.setStyleSheet("""
            QFrame {
                background-color: transparent;
                border-bottom: 1px solid #45475a;
                padding: 5px;
            }
        """)
        self.setFixedHeight(50)  # 固定高度，防止被压缩
        self.setCursor(Qt.OpenHandCursor)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)
        
        # 标题
        self.title_label = QLabel(self.title)
        self.title_label.setStyleSheet("color: #89b4fa; font-size: 18px; font-weight: bold; border: none;")
        layout.addWidget(self.title_label)
        layout.addStretch()
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_start_pos = event.pos()
        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event):
        if self._drag_start_pos and (event.pos() - self._drag_start_pos).manhattanLength() > 10:
            drag = QDrag(self)
            mime_data = QMimeData()
            mime_data.setText(f"subcategory:{self.title}")
            drag.setMimeData(mime_data)
            
            # 创建拖拽时的预览图
            pixmap = self.grab()
            drag.setPixmap(pixmap.scaled(300, 50, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            drag.setHotSpot(event.pos())
            
            self.drag_started.emit(self)
            drag.exec_(Qt.MoveAction)
        super().mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event):
        self._drag_start_pos = None
        super().mouseReleaseEvent(event)


class DraggableCategoryButton(QPushButton):
    """可拖动的分类按钮"""
    drag_started = pyqtSignal(object)
    
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self._drag_start_pos = None
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_start_pos = event.pos()
        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event):
        if self._drag_start_pos and (event.pos() - self._drag_start_pos).manhattanLength() > 10:
            drag = QDrag(self)
            mime_data = QMimeData()
            mime_data.setText(f"category:{self.text()}")
            drag.setMimeData(mime_data)
            
            pixmap = self.grab()
            drag.setPixmap(pixmap)
            drag.setHotSpot(event.pos())
            
            self.drag_started.emit(self)
            drag.exec_(Qt.MoveAction)
            self._drag_start_pos = None
        super().mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event):
        self._drag_start_pos = None
        super().mouseReleaseEvent(event)


class ToolCard(QFrame):
    """工具卡片组件"""
    drag_started = pyqtSignal(object)  # 拖拽开始信号
    
    def __init__(self, tool_data, parent=None):
        super().__init__(parent)
        self.tool_data = tool_data
        self._selected = False
        self._drag_start_pos = None
        self.init_ui()

    def init_ui(self):
        self.update_style()
        self.setCursor(Qt.PointingHandCursor)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(5)

        # 工具名称
        self.name_label = QLabel(self.tool_data.get("name", "未命名"))
        self.name_label.setStyleSheet("color: #cdd6f4; font-size: 20px; font-weight: bold;")
        layout.addWidget(self.name_label)

        # 描述
        desc = self.tool_data.get("description", "")
        if desc:
            desc_label = QLabel(desc)
            desc_label.setWordWrap(True)
            desc_label.setStyleSheet("color: #a6adc8; font-size: 16px;")
            layout.addWidget(desc_label)


    def update_style(self):
        """根据选中状态更新样式"""
        if self._selected:
            self.setStyleSheet("""
                QFrame {
                    background-color: #89b4fa;
                    border-radius: 8px;
                    padding: 5px;
                }
            """)
            # 更新子标签颜色
            for child in self.findChildren(QLabel):
                if child.objectName() != "cmd_label":
                    child.setStyleSheet(child.styleSheet().replace("#cdd6f4", "#1e1e2e").replace("#a6adc8", "#313244"))
        else:
            self.setStyleSheet("""
                QFrame {
                    background-color: #313244;
                    border-radius: 8px;
                    padding: 5px;
                }
                QFrame:hover {
                    background-color: #45475a;
                }
            """)

    def mousePressEvent(self, event):
        """点击卡片切换选中状态"""
        if event.button() == Qt.LeftButton:
            self._drag_start_pos = event.pos()
        super().mousePressEvent(event)
    
    def mouseReleaseEvent(self, event):
        """鼠标释放时切换选中状态"""
        if event.button() == Qt.LeftButton and self._drag_start_pos:
            # 只有在没有拖拽的情况下才切换选中状态
            if (event.pos() - self._drag_start_pos).manhattanLength() < 10:
                self.set_selected(not self._selected)
        self._drag_start_pos = None
        super().mouseReleaseEvent(event)
    
    def mouseDoubleClickEvent(self, event):
        """双击进入编辑界面"""
        if event.button() == Qt.LeftButton:
            # 发出双击信号
            if hasattr(self, 'edit_callback') and self.edit_callback:
                self.edit_callback(self.tool_data)
        super().mouseDoubleClickEvent(event)
    
    def mouseMoveEvent(self, event):
        """拖拽开始"""
        if self._drag_start_pos and (event.pos() - self._drag_start_pos).manhattanLength() > 10:
            drag = QDrag(self)
            mime_data = QMimeData()
            mime_data.setText(self.tool_data.get("name", ""))
            drag.setMimeData(mime_data)
            
            # 创建拖拽时的预览图
            pixmap = self.grab()
            drag.setPixmap(pixmap.scaled(200, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            drag.setHotSpot(event.pos())
            
            self.drag_started.emit(self)
            drag.exec_(Qt.MoveAction)
        super().mouseMoveEvent(event)

    def is_selected(self):
        return self._selected

    def set_selected(self, selected):
        self._selected = selected
        self.update_style()
        # 更新标签颜色
        if hasattr(self, 'name_label'):
            if selected:
                self.name_label.setStyleSheet("color: #1e1e2e; font-size: 20px; font-weight: bold;")
            else:
                self.name_label.setStyleSheet("color: #cdd6f4; font-size: 20px; font-weight: bold;")


class MainWindow(QMainWindow):
    """主窗口"""
    def __init__(self):
        super().__init__()
        self.tools = []
        self.categories = ["信息收集", "漏洞扫描", "Web测试", "密码破解", "其他"]
        self.subcategories = {}  # 子分类: {category: [subcategory_name, ...]}
        self.tool_cards = []
        self.subcategory_headers = []  # 子分类标题组件列表
        self.load_config()
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Stars_Falling")
        self.setWindowIcon(QIcon(resource_path("icon_512.ico")))
        self.setMinimumSize(1300, 900)
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1e1e2e;
            }
            QWidget {
                background-color: #1e1e2e;
                color: #cdd6f4;
            }
            QSplitter::handle {
                background-color: #45475a;
            }
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:vertical {
                background-color: #1e1e2e;
                width: 10px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical {
                background-color: #45475a;
                border-radius: 5px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #6c7086;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)

        # 主布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 左侧分类面板
        self.category_panel = self.create_category_panel()
        main_layout.addWidget(self.category_panel)

        # 右侧主内容区
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(20, 20, 20, 20)
        right_layout.setSpacing(15)

        # 顶部控制栏
        top_bar = self.create_top_bar()
        right_layout.addWidget(top_bar)

        # 工具网格区域
        tools_widget = self.create_tools_area()
        right_layout.addWidget(tools_widget)

        main_layout.addWidget(right_widget, 1)

        # 初始显示所有工具
        self.filter_tools_by_category("全部")

    def create_category_panel(self):
        """创建左侧分类面板"""
        panel = QFrame()
        panel.setFixedWidth(200)
        panel.setStyleSheet("""
            QFrame {
                background-color: #181825;
                border-right: 1px solid #313244;
            }
            QPushButton {
                background-color: transparent;
                color: #cdd6f4;
                border: none;
                border-radius: 8px;
                padding: 12px 15px;
                text-align: left;
                font-size: 20px;
            }
            QPushButton:hover {
                background-color: #313244;
            }
            QPushButton:checked {
                background-color: #89b4fa;
                color: #1e1e2e;
                font-weight: bold;
            }
        """)

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(10, 20, 10, 20)
        layout.setSpacing(5)

        # 标题
        title = QLabel("工具分类")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #cdd6f4; padding: 10px;")
        layout.addWidget(title)

        # 分类按钮组
        self.category_buttons = []
        self.dragging_category_btn = None
        
        # 全部分类（不可拖动）
        all_btn = QPushButton("全部")
        all_btn.setCheckable(True)
        all_btn.setChecked(True)
        all_btn.clicked.connect(lambda: self.on_category_clicked("全部"))
        self.category_buttons.append(all_btn)
        layout.addWidget(all_btn)

        # 各分类（可拖动）
        for cat in self.categories:
            btn = DraggableCategoryButton(cat)
            btn.clicked.connect(lambda checked, c=cat: self.on_category_clicked(c))
            btn.drag_started.connect(self.on_category_drag_started)
            btn.setContextMenuPolicy(Qt.CustomContextMenu)
            btn.customContextMenuRequested.connect(lambda pos, c=cat, b=btn: self.show_category_btn_context_menu(pos, c, b))
            self.category_buttons.append(btn)
            layout.addWidget(btn)

        layout.addStretch()

        # 设置分类面板右键菜单和拖放（空白区域）
        panel.setContextMenuPolicy(Qt.CustomContextMenu)
        panel.customContextMenuRequested.connect(self.show_category_context_menu)
        panel.setAcceptDrops(True)
        panel.dragEnterEvent = self.category_drag_enter
        panel.dragMoveEvent = self.category_drag_move
        panel.dropEvent = self.category_drop

        return panel
    
    def on_category_drag_started(self, btn):
        """记录正在拖拽的分类按钮"""
        self.dragging_category_btn = btn
    
    def category_drag_enter(self, event):
        """分类拖拽进入事件"""
        if event.mimeData().hasText() and event.mimeData().text().startswith("category:"):
            event.acceptProposedAction()
    
    def category_drag_move(self, event):
        """分类拖拽移动事件"""
        if event.mimeData().hasText() and event.mimeData().text().startswith("category:"):
            event.acceptProposedAction()
    
    def category_drop(self, event):
        """分类拖拽放下事件"""
        if not event.mimeData().hasText() or not event.mimeData().text().startswith("category:"):
            return
        
        dragged_cat = event.mimeData().text().replace("category:", "")
        if dragged_cat not in self.categories:
            return
        
        drop_pos = event.pos()
        
        # 找到目标位置（跳过"全部"按钮）
        target_index = len(self.categories)
        for i, btn in enumerate(self.category_buttons[1:]):  # 跳过"全部"
            btn_rect = btn.geometry()
            if drop_pos.y() < btn_rect.center().y():
                target_index = i
                break
        
        # 获取当前分类的索引
        drag_index = self.categories.index(dragged_cat)
        
        if drag_index != target_index and target_index != drag_index + 1:
            self.categories.remove(dragged_cat)
            if target_index > drag_index:
                target_index -= 1
            self.categories.insert(target_index, dragged_cat)
            self.save_config()
            self.refresh_category_panel()
            # 保持当前选中的分类
            current_cat = getattr(self, 'current_category', '全部')
            for btn in self.category_buttons:
                btn.setChecked(btn.text() == current_cat)
        
        self.dragging_category_btn = None
        event.acceptProposedAction()

    def create_top_bar(self):
        """创建顶部控制栏"""
        bar = QFrame()
        bar.setStyleSheet("""
            QFrame {
                background-color: #313244;
                border-radius: 10px;
                padding: 10px;
            }
            QLineEdit {
                background-color: #45475a;
                color: #cdd6f4;
                border: 1px solid #6c7086;
                border-radius: 5px;
                padding: 10px;
                font-size: 18px;
            }
            QLineEdit:focus {
                border: 1px solid #89b4fa;
            }
            QPushButton {
                background-color: #89b4fa;
                color: #1e1e2e;
                border: none;
                border-radius: 5px;
                padding: 12px 24px;
                font-size: 18px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #b4befe;
            }
        """)

        layout = QHBoxLayout(bar)
        layout.setSpacing(10)

        # URL输入
        url_label = QLabel("目标URL:")
        url_label.setStyleSheet("color: #cdd6f4; font-size: 18px; font-weight: bold;")
        layout.addWidget(url_label)

        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("输入目标URL，例如: http://example.com 或 192.168.1.1")
        self.url_input.setMinimumWidth(400)
        layout.addWidget(self.url_input, 1)

        # 全选/取消全选
        self.select_all_btn = QPushButton("全选")
        self.select_all_btn.setStyleSheet("background-color: #6c7086;")
        self.select_all_btn.clicked.connect(self.toggle_select_all)
        layout.addWidget(self.select_all_btn)

        # 执行按钮
        self.execute_btn = QPushButton("▶️ 启动")
        self.execute_btn.clicked.connect(self.execute_selected_tools)
        layout.addWidget(self.execute_btn)

        return bar

    def create_tools_area(self):
        """创建工具显示区域"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)

        # 工具数量标签
        self.tools_count_label = QLabel("工具列表 (0)")
        self.tools_count_label.setStyleSheet("font-size: 22px; font-weight: bold; color: #cdd6f4;")
        layout.addWidget(self.tools_count_label)

        # 滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background-color: transparent;")

        self.tools_container = QWidget()
        self.tools_container.setAcceptDrops(True)
        self.tools_layout = QGridLayout(self.tools_container)
        self.tools_layout.setSpacing(10)
        self.tools_layout.setAlignment(Qt.AlignTop)
        # 设置4列均匀拉伸
        for i in range(4):
            self.tools_layout.setColumnStretch(i, 1)

        scroll.setWidget(self.tools_container)
        
        # 设置工具区域右键菜单
        self.tools_container.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tools_container.customContextMenuRequested.connect(self.show_tools_area_context_menu)
        
        # 拖放事件
        self.tools_container.dragEnterEvent = self.tools_drag_enter
        self.tools_container.dropEvent = self.tools_drop
        self.tools_container.dragMoveEvent = self.tools_drag_move
        self.dragging_card = None
        self.dragging_subcategory = None
        
        layout.addWidget(scroll)

        return widget

    def on_category_clicked(self, category):
        """分类点击事件"""
        for btn in self.category_buttons:
            btn.setChecked(False)
        
        sender = self.sender()
        if sender:
            sender.setChecked(True)
        
        self.filter_tools_by_category(category)

    def filter_tools_by_category(self, category):
        """按分类筛选工具"""
        self.current_category = category  # 记录当前分类
        
        # 清空现有卡片和子分类标题
        for card in self.tool_cards:
            card.setParent(None)
            card.deleteLater()
        self.tool_cards.clear()
        
        for header in self.subcategory_headers:
            header.setParent(None)
            header.deleteLater()
        self.subcategory_headers.clear()

        # 筛选工具
        row, col = 0, 0
        max_cols = 4
        
        if category == "全部":
            # 全部分类时按分类和子分类分组显示
            for cat in self.categories:
                cat_tools = [t for t in self.tools if t.get("category") == cat]
                if not cat_tools:
                    continue
                
                # 添加分类标题
                if col != 0:
                    row += 1
                    col = 0
                cat_header = SubCategoryHeader(f"【{cat}】")
                cat_header.title_label.setStyleSheet("color: #f9e2af; font-size: 20px; font-weight: bold; border: none;")
                self.tools_layout.addWidget(cat_header, row, 0, 1, max_cols)
                self.subcategory_headers.append(cat_header)
                row += 1
                
                # 显示该分类下无子分类的工具
                tools_without_subcat = [t for t in cat_tools if not t.get("subcategory")]
                for tool in tools_without_subcat:
                    card = ToolCard(tool)
                    card.setContextMenuPolicy(Qt.CustomContextMenu)
                    card.customContextMenuRequested.connect(lambda pos, t=tool, c=card: self.show_tool_context_menu(pos, t, c))
                    card.drag_started.connect(self.on_card_drag_started)
                    card.edit_callback = self.edit_tool
                    self.tools_layout.addWidget(card, row, col)
                    self.tool_cards.append(card)
                    col += 1
                    if col >= max_cols:
                        col = 0
                        row += 1
                
                # 显示该分类下的子分类及其工具
                subcats = self.subcategories.get(cat, [])
                for subcat in subcats:
                    subcat_tools = [t for t in cat_tools if t.get("subcategory") == subcat]
                    if not subcat_tools:
                        continue
                    
                    if col != 0:
                        row += 1
                        col = 0
                    
                    subcat_header = SubCategoryHeader(f"  {subcat}")
                    self.tools_layout.addWidget(subcat_header, row, 0, 1, max_cols)
                    self.subcategory_headers.append(subcat_header)
                    row += 1
                    
                    for tool in subcat_tools:
                        card = ToolCard(tool)
                        card.setContextMenuPolicy(Qt.CustomContextMenu)
                        card.customContextMenuRequested.connect(lambda pos, t=tool, c=card: self.show_tool_context_menu(pos, t, c))
                        card.drag_started.connect(self.on_card_drag_started)
                        card.edit_callback = self.edit_tool
                        self.tools_layout.addWidget(card, row, col)
                        self.tool_cards.append(card)
                        col += 1
                        if col >= max_cols:
                            col = 0
                            row += 1
            
            self.tools_count_label.setText(f"工具列表 ({len(self.tools)})")
            return
        
        # 非全部分类
        filtered_tools = [t for t in self.tools if t.get("category") == category]
        subcats = self.subcategories.get(category, [])

        # 先显示没有子分类的工具
        tools_without_subcat = [t for t in filtered_tools if not t.get("subcategory")]
        for tool in tools_without_subcat:
            card = ToolCard(tool)
            card.setContextMenuPolicy(Qt.CustomContextMenu)
            card.customContextMenuRequested.connect(lambda pos, t=tool, c=card: self.show_tool_context_menu(pos, t, c))
            card.drag_started.connect(self.on_card_drag_started)
            card.edit_callback = self.edit_tool
            self.tools_layout.addWidget(card, row, col)
            self.tool_cards.append(card)
            col += 1
            if col >= max_cols:
                col = 0
                row += 1
        
        # 按子分类显示工具
        for subcat in subcats:
            # 换行显示子分类标题
            if col != 0:
                row += 1
                col = 0
            
            # 添加子分类标题
            header = SubCategoryHeader(subcat)
            header.setContextMenuPolicy(Qt.CustomContextMenu)
            header.customContextMenuRequested.connect(lambda pos, s=subcat, h=header: self.show_subcategory_context_menu(pos, s, h))
            header.drag_started.connect(self.on_subcategory_drag_started)
            self.tools_layout.addWidget(header, row, 0, 1, max_cols)
            self.subcategory_headers.append(header)
            row += 1
            
            # 显示该子分类下的工具
            subcat_tools = [t for t in filtered_tools if t.get("subcategory") == subcat]
            for tool in subcat_tools:
                card = ToolCard(tool)
                card.setContextMenuPolicy(Qt.CustomContextMenu)
                card.customContextMenuRequested.connect(lambda pos, t=tool, c=card: self.show_tool_context_menu(pos, t, c))
                card.drag_started.connect(self.on_card_drag_started)
                card.edit_callback = self.edit_tool
                self.tools_layout.addWidget(card, row, col)
                self.tool_cards.append(card)
                col += 1
                if col >= max_cols:
                    col = 0
                    row += 1

        self.tools_count_label.setText(f"工具列表 ({len(filtered_tools)})")

    def show_tool_context_menu(self, pos, tool, card):
        """显示工具右键菜单"""
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #313244;
                color: #cdd6f4;
                border: 1px solid #45475a;
                border-radius: 5px;
                padding: 5px;
            }
            QMenu::item {
                padding: 8px 20px;
                border-radius: 3px;
            }
            QMenu::item:selected {
                background-color: #45475a;
            }
        """)

        edit_action = menu.addAction("编辑")
        edit_action.triggered.connect(lambda: self.edit_tool(tool))

        # 复制到子菜单
        copy_menu = menu.addMenu("复制到")
        copy_menu.setStyleSheet("""
            QMenu {
                background-color: #313244;
                color: #cdd6f4;
                border: 1px solid #45475a;
                border-radius: 5px;
                padding: 5px;
            }
            QMenu::item {
                padding: 8px 20px;
                border-radius: 3px;
            }
            QMenu::item:selected {
                background-color: #45475a;
            }
        """)
        for cat in self.categories:
            cat_action = copy_menu.addAction(cat)
            cat_action.triggered.connect(lambda checked, c=cat: self.copy_tool_to_category(tool, c))

        # 移动到子分类（只在非"全部"分类时显示）
        if hasattr(self, 'current_category') and self.current_category != "全部":
            subcats = self.subcategories.get(self.current_category, [])
            if subcats:
                subcat_menu = menu.addMenu("移动到子分类")
                subcat_menu.setStyleSheet("""
                    QMenu {
                        background-color: #313244;
                        color: #cdd6f4;
                        border: 1px solid #45475a;
                        border-radius: 5px;
                        padding: 5px;
                    }
                    QMenu::item {
                        padding: 8px 20px;
                        border-radius: 3px;
                    }
                    QMenu::item:selected {
                        background-color: #45475a;
                    }
                """)
                # 添加"无子分类"选项
                none_action = subcat_menu.addAction("(无子分类)")
                none_action.triggered.connect(lambda: self.move_tool_to_subcategory(tool, ""))
                subcat_menu.addSeparator()
                for subcat in subcats:
                    subcat_action = subcat_menu.addAction(subcat)
                    subcat_action.triggered.connect(lambda checked, s=subcat: self.move_tool_to_subcategory(tool, s))

        delete_action = menu.addAction("删除")
        delete_action.triggered.connect(lambda: self.delete_tool(tool))

        menu.exec_(card.mapToGlobal(pos))
    
    def move_tool_to_subcategory(self, tool, subcategory):
        """移动工具到子分类"""
        tool["subcategory"] = subcategory
        self.save_config()
        self.filter_tools_by_category(self.current_category)

    def add_tool(self):
        """添加工具"""
        # 确定默认分类
        current_cat = getattr(self, 'current_category', '全部')
        if current_cat == "全部":
            default_cat = self.categories[0] if self.categories else ""
        else:
            default_cat = current_cat
        
        dialog = AddToolDialog(self, self.categories)
        # 设置默认分类
        if default_cat:
            dialog.category_combo.setCurrentText(default_cat)
        if dialog.exec_() == QDialog.Accepted:
            tool_data = dialog.get_tool_data()
            if tool_data["name"]:
                self.tools.append(tool_data)
                # 添加新分类
                if tool_data["category"] and tool_data["category"] not in self.categories:
                    self.categories.append(tool_data["category"])
                    self.refresh_category_panel()
                self.save_config()
                # 保持在当前分类
                current_cat = getattr(self, 'current_category', '全部')
                self.filter_tools_by_category(current_cat)

    def edit_tool(self, tool):
        """编辑工具"""
        dialog = AddToolDialog(self, self.categories, tool)
        if dialog.exec_() == QDialog.Accepted:
            new_data = dialog.get_tool_data()
            idx = self.tools.index(tool)
            self.tools[idx] = new_data
            if new_data["category"] and new_data["category"] not in self.categories:
                self.categories.append(new_data["category"])
                self.refresh_category_panel()
            self.save_config()
            # 保持在当前分类
            current_cat = getattr(self, 'current_category', '全部')
            self.filter_tools_by_category(current_cat)

    def copy_tool_to_category(self, tool, category):
        """复制工具到指定分类"""
        # 创建工具副本
        new_tool = tool.copy()
        new_tool["category"] = category
        new_tool["subcategory"] = ""  # 清除子分类
        self.tools.append(new_tool)
        self.save_config()
        # 保持在当前分类
        current_cat = getattr(self, 'current_category', '全部')
        self.filter_tools_by_category(current_cat)

    def delete_tool(self, tool):
        """删除工具"""
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("确认删除")
        msg_box.setText(f"确定要删除工具 '{tool.get('name')}' 吗？")
        msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg_box.setDefaultButton(QMessageBox.No)
        # 去掉问号图标
        msg_box.setWindowFlags(msg_box.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        msg_box.setStyleSheet("""
            QMessageBox {
                background-color: #1e1e2e;
            }
            QMessageBox QLabel {
                color: #cdd6f4;
                font-size: 16px;
            }
            QPushButton {
                background-color: #89b4fa;
                color: #1e1e2e;
                border: none;
                border-radius: 5px;
                padding: 8px 20px;
                font-size: 14px;
                font-weight: bold;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #b4befe;
            }
        """)
        # 设置深色标题栏
        if sys.platform == 'win32':
            try:
                hwnd = int(msg_box.winId())
                DWMWA_USE_IMMERSIVE_DARK_MODE = 20
                DWMWA_CAPTION_COLOR = 35
                ctypes.windll.dwmapi.DwmSetWindowAttribute(
                    hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE,
                    ctypes.byref(ctypes.c_int(1)), ctypes.sizeof(ctypes.c_int)
                )
                color = 0x002e1e1e  # BGR: #1e1e2e
                ctypes.windll.dwmapi.DwmSetWindowAttribute(
                    hwnd, DWMWA_CAPTION_COLOR,
                    ctypes.byref(ctypes.c_int(color)), ctypes.sizeof(ctypes.c_int)
                )
            except:
                pass
        
        if msg_box.exec_() == QMessageBox.Yes:
            self.tools.remove(tool)
            self.save_config()
            # 保持在当前分类
            current_cat = getattr(self, 'current_category', '全部')
            self.filter_tools_by_category(current_cat)

    def on_card_drag_started(self, card):
        """记录正在拖拽的卡片"""
        self.dragging_card = card
        self.dragging_subcategory = None
    
    def on_subcategory_drag_started(self, header):
        """记录正在拖拽的子分类"""
        self.dragging_subcategory = header
        self.dragging_card = None
    
    def tools_drag_enter(self, event):
        """拖拽进入事件"""
        if event.mimeData().hasText():
            event.acceptProposedAction()
    
    def tools_drag_move(self, event):
        """拖拽移动事件"""
        if event.mimeData().hasText():
            event.acceptProposedAction()
    
    def tools_drop(self, event):
        """拖拽放下事件"""
        if not event.mimeData().hasText():
            return
        
        drop_pos = event.pos()
        current_cat = getattr(self, 'current_category', '全部')
        mime_text = event.mimeData().text()
        
        # 处理子分类拖拽
        if mime_text.startswith("subcategory:") and self.dragging_subcategory:
            dragged_subcat = mime_text.replace("subcategory:", "")
            
            # 找到目标位置
            target_index = len(self.subcategory_headers)
            for i, header in enumerate(self.subcategory_headers):
                header_rect = header.geometry()
                if drop_pos.y() < header_rect.center().y():
                    target_index = i
                    break
            
            # 获取当前子分类在列表中的索引
            subcats = self.subcategories.get(current_cat, [])
            if dragged_subcat in subcats:
                drag_index = subcats.index(dragged_subcat)
                if drag_index != target_index and target_index != drag_index + 1:
                    subcats.remove(dragged_subcat)
                    if target_index > drag_index:
                        target_index -= 1
                    subcats.insert(target_index, dragged_subcat)
                    self.subcategories[current_cat] = subcats
                    self.save_config()
                    self.filter_tools_by_category(current_cat)
            
            self.dragging_subcategory = None
            event.acceptProposedAction()
            return
        
        # 处理工具卡片拖拽
        if not self.dragging_card:
            return
        
        tool_data = self.dragging_card.tool_data
        
        # 检查是否拖到子分类标题上
        for header in self.subcategory_headers:
            header_rect = header.geometry()
            if header_rect.contains(drop_pos):
                # 移动到该子分类
                tool_data["subcategory"] = header.title
                self.save_config()
                self.filter_tools_by_category(current_cat)
                self.dragging_card = None
                event.acceptProposedAction()
                return
        
        # 检查是否拖到子分类标题下方的区域（移动到该子分类）
        target_subcategory = ""
        for i, header in enumerate(self.subcategory_headers):
            header_rect = header.geometry()
            # 找到下一个子分类标题或底部
            next_header_top = float('inf')
            if i + 1 < len(self.subcategory_headers):
                next_header_top = self.subcategory_headers[i + 1].geometry().top()
            
            # 如果在当前子分类标题下方，且在下一个子分类标题上方
            if drop_pos.y() > header_rect.bottom() and drop_pos.y() < next_header_top:
                target_subcategory = header.title
                break
        
        # 检查是否拖到子分类标题上方的无子分类区域
        if self.subcategory_headers:
            first_header_top = self.subcategory_headers[0].geometry().top()
            if drop_pos.y() < first_header_top:
                target_subcategory = ""
        
        # 如果目标子分类与当前不同，更新子分类
        if tool_data.get("subcategory", "") != target_subcategory:
            tool_data["subcategory"] = target_subcategory
            self.save_config()
            self.filter_tools_by_category(current_cat)
            self.dragging_card = None
            event.acceptProposedAction()
            return
        
        # 同一子分类内的排序
        # 找到放下位置的卡片
        target_card = None
        target_index = len(self.tool_cards)
        
        for i, card in enumerate(self.tool_cards):
            card_rect = card.geometry()
            if card_rect.contains(drop_pos):
                target_card = card
                target_index = i
                break
            # 如果在卡片之间，找到最近的位置
            elif drop_pos.x() < card_rect.right() and drop_pos.y() < card_rect.bottom():
                target_index = i
                break
        
        # 获取拖拽卡片的索引
        drag_index = self.tool_cards.index(self.dragging_card) if self.dragging_card in self.tool_cards else -1
        
        if drag_index >= 0 and drag_index != target_index:
            # 更新 tools 列表顺序
            if tool_data in self.tools:
                self.tools.remove(tool_data)
                # 计算新位置
                if target_index > drag_index:
                    target_index -= 1
                self.tools.insert(target_index, tool_data)
                self.save_config()
                self.filter_tools_by_category(current_cat)
        
        self.dragging_card = None
        event.acceptProposedAction()

    def toggle_select_all(self):
        """全选/取消全选"""
        all_selected = all(card.is_selected() for card in self.tool_cards) if self.tool_cards else False
        for card in self.tool_cards:
            card.set_selected(not all_selected)
        self.select_all_btn.setText("取消全选" if not all_selected else "全选")

    def execute_selected_tools(self):
        """执行选中的工具"""
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "警告", "请输入目标URL")
            return

        selected_tools = []
        for card in self.tool_cards:
            if card.is_selected():
                selected_tools.append(card.tool_data)

        if not selected_tools:
            QMessageBox.warning(self, "警告", "请至少选择一个工具")
            return

        # 为每个工具打开独立窗口
        for tool in selected_tools:
            path = tool.get("path", "").strip()  # 工具路径
            params = tool.get("command", "").replace("{url}", url)  # 参数
            startdir = tool.get("startdir", "") or None  # 起始位置
            tool_name = tool.get("name", "未知")
            
            if path:
                # 有路径时直接启动
                full_command = f"{path} {params}".strip()
                subprocess.Popen(full_command, shell=True, cwd=startdir)
            else:
                # 路径为空时使用 cmd 窗口启动
                cmd_command = f'start cmd /k "{params}"'
                subprocess.Popen(cmd_command, shell=True, cwd=startdir)

    def show_category_context_menu(self, pos):
        """显示分类区域右键菜单（空白区域）"""
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #313244;
                color: #cdd6f4;
                border: 1px solid #45475a;
                border-radius: 5px;
                padding: 5px;
            }
            QMenu::item {
                padding: 8px 20px;
                border-radius: 3px;
            }
            QMenu::item:selected {
                background-color: #45475a;
            }
        """)

        add_action = menu.addAction("添加分类")
        add_action.triggered.connect(self.add_category_from_menu)

        menu.exec_(self.category_panel.mapToGlobal(pos))
    
    def show_category_btn_context_menu(self, pos, category, btn):
        """显示分类按钮右键菜单"""
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #313244;
                color: #cdd6f4;
                border: 1px solid #45475a;
                border-radius: 5px;
                padding: 5px;
            }
            QMenu::item {
                padding: 8px 20px;
                border-radius: 3px;
            }
            QMenu::item:selected {
                background-color: #45475a;
            }
        """)

        add_action = menu.addAction("添加分类")
        add_action.triggered.connect(self.add_category_from_menu)
        
        rename_action = menu.addAction("重命名")
        rename_action.triggered.connect(lambda: self.rename_category(category))
        
        delete_action = menu.addAction("删除分类")
        delete_action.triggered.connect(lambda: self.delete_category(category))

        menu.exec_(btn.mapToGlobal(pos))

    def add_category_from_menu(self):
        """从右键菜单添加分类"""
        dialog = DarkInputDialog(self, "添加分类", "分类名称:")
        if dialog.exec_() == QDialog.Accepted:
            text = dialog.get_text()
            if text.strip() and text.strip() not in self.categories:
                self.categories.append(text.strip())
                self.refresh_category_panel()
                self.save_config()

    def rename_category(self, old_name):
        """重命名分类"""
        dialog = DarkInputDialog(self, "重命名分类", "新名称:", text=old_name)
        if dialog.exec_() == QDialog.Accepted:
            new_name = dialog.get_text().strip()
            if new_name and new_name != old_name and new_name not in self.categories:
                # 更新分类列表
                idx = self.categories.index(old_name)
                self.categories[idx] = new_name
                # 更新工具的分类
                for tool in self.tools:
                    if tool.get("category") == old_name:
                        tool["category"] = new_name
                # 更新子分类
                if old_name in self.subcategories:
                    self.subcategories[new_name] = self.subcategories.pop(old_name)
                self.refresh_category_panel()
                self.save_config()
                # 如果当前在该分类，更新显示
                if getattr(self, 'current_category', '') == old_name:
                    self.filter_tools_by_category(new_name)
                    for btn in self.category_buttons:
                        btn.setChecked(btn.text() == new_name)
    
    def delete_category(self, category):
        """删除指定分类"""
        # 删除该分类下的所有工具
        self.tools = [t for t in self.tools if t.get("category") != category]
        # 删除该分类的子分类
        if category in self.subcategories:
            del self.subcategories[category]
        # 删除分类
        self.categories.remove(category)
        self.refresh_category_panel()
        self.save_config()
        # 切换到全部分类
        self.filter_tools_by_category("全部")
        for btn in self.category_buttons:
            btn.setChecked(btn.text() == "全部")

    def show_tools_area_context_menu(self, pos):
        """显示工具区域右键菜单"""
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #313244;
                color: #cdd6f4;
                border: 1px solid #45475a;
                border-radius: 5px;
                padding: 5px;
            }
            QMenu::item {
                padding: 8px 20px;
                border-radius: 3px;
            }
            QMenu::item:selected {
                background-color: #45475a;
            }
        """)

        add_action = menu.addAction("添加工具")
        add_action.triggered.connect(self.add_tool)
        
        # 只有在非"全部"分类时才显示添加子分类选项
        if hasattr(self, 'current_category') and self.current_category != "全部":
            add_subcat_action = menu.addAction("添加子分类")
            add_subcat_action.triggered.connect(self.add_subcategory)

        menu.exec_(self.tools_container.mapToGlobal(pos))
    
    def add_subcategory(self):
        """添加子分类"""
        if not hasattr(self, 'current_category') or self.current_category == "全部":
            return
        
        dialog = DarkInputDialog(self, "添加子分类", "子分类名称:")
        if dialog.exec_() == QDialog.Accepted:
            text = dialog.get_text().strip()
            if text:
                if self.current_category not in self.subcategories:
                    self.subcategories[self.current_category] = []
                if text not in self.subcategories[self.current_category]:
                    self.subcategories[self.current_category].append(text)
                    self.save_config()
                    self.filter_tools_by_category(self.current_category)
    
    def show_subcategory_context_menu(self, pos, subcategory, header):
        """显示子分类标题右键菜单"""
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #313244;
                color: #cdd6f4;
                border: 1px solid #45475a;
                border-radius: 5px;
                padding: 5px;
            }
            QMenu::item {
                padding: 8px 20px;
                border-radius: 3px;
            }
            QMenu::item:selected {
                background-color: #45475a;
            }
        """)
        
        add_tool_action = menu.addAction("添加工具到此子分类")
        add_tool_action.triggered.connect(lambda: self.add_tool_to_subcategory(subcategory))
        
        menu.addSeparator()
        
        rename_action = menu.addAction("重命名")
        rename_action.triggered.connect(lambda: self.rename_subcategory(subcategory))
        
        delete_action = menu.addAction("删除子分类")
        delete_action.triggered.connect(lambda: self.delete_subcategory(subcategory))
        
        menu.exec_(header.mapToGlobal(pos))
    
    def add_tool_to_subcategory(self, subcategory):
        """添加工具到指定子分类"""
        dialog = AddToolDialog(self, self.categories)
        # 预设分类为当前分类
        dialog.category_combo.setCurrentText(self.current_category)
        if dialog.exec_() == QDialog.Accepted:
            tool_data = dialog.get_tool_data()
            if tool_data["name"]:
                tool_data["subcategory"] = subcategory  # 设置子分类
                self.tools.append(tool_data)
                self.save_config()
                self.filter_tools_by_category(self.current_category)
    
    def rename_subcategory(self, old_name):
        """重命名子分类"""
        dialog = DarkInputDialog(self, "重命名子分类", "新名称:", text=old_name)
        if dialog.exec_() == QDialog.Accepted:
            new_name = dialog.get_text().strip()
            if new_name and new_name != old_name:
                # 更新子分类列表
                if self.current_category in self.subcategories:
                    idx = self.subcategories[self.current_category].index(old_name)
                    self.subcategories[self.current_category][idx] = new_name
                # 更新工具的子分类
                for tool in self.tools:
                    if tool.get("category") == self.current_category and tool.get("subcategory") == old_name:
                        tool["subcategory"] = new_name
                self.save_config()
                self.filter_tools_by_category(self.current_category)
    
    def delete_subcategory(self, subcategory):
        """删除子分类"""
        # 将该子分类下的工具移到无子分类
        for tool in self.tools:
            if tool.get("category") == self.current_category and tool.get("subcategory") == subcategory:
                tool["subcategory"] = ""
        # 从子分类列表中移除
        if self.current_category in self.subcategories and subcategory in self.subcategories[self.current_category]:
            self.subcategories[self.current_category].remove(subcategory)
        self.save_config()
        self.filter_tools_by_category(self.current_category)

    def refresh_category_panel(self):
        """刷新分类面板"""
        # 移除旧按钮（保留"全部"按钮）
        for btn in self.category_buttons[1:]:
            btn.setParent(None)
            btn.deleteLater()
        self.category_buttons = self.category_buttons[:1]

        # 重新添加分类按钮
        layout = self.category_panel.layout()
        
        for cat in self.categories:
            btn = DraggableCategoryButton(cat)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: #cdd6f4;
                    border: none;
                    border-radius: 8px;
                    padding: 12px 15px;
                    text-align: left;
                    font-size: 20px;
                }
                QPushButton:hover {
                    background-color: #313244;
                }
                QPushButton:checked {
                    background-color: #89b4fa;
                    color: #1e1e2e;
                    font-weight: bold;
                }
            """)
            btn.clicked.connect(lambda checked, c=cat: self.on_category_clicked(c))
            btn.drag_started.connect(self.on_category_drag_started)
            btn.setContextMenuPolicy(Qt.CustomContextMenu)
            btn.customContextMenuRequested.connect(lambda pos, c=cat, b=btn: self.show_category_btn_context_menu(pos, c, b))
            self.category_buttons.append(btn)
            layout.insertWidget(layout.count() - 1, btn)  # 在stretch之前插入

    def load_config(self):
        """加载配置"""
        config_path = Path(CONFIG_FILE)
        if config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.tools = data.get("tools", [])
                    saved_categories = data.get("categories", [])
                    if saved_categories:
                        self.categories = saved_categories
                    self.subcategories = data.get("subcategories", {})
            except Exception as e:
                print(f"加载配置失败: {e}")

    def save_config(self):
        """保存配置"""
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump({
                    "tools": self.tools,
                    "categories": self.categories,
                    "subcategories": self.subcategories
                }, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存配置失败: {e}")


def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    # 设置深色主题
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(30, 30, 46))
    palette.setColor(QPalette.WindowText, QColor(205, 214, 244))
    palette.setColor(QPalette.Base, QColor(49, 50, 68))
    palette.setColor(QPalette.AlternateBase, QColor(30, 30, 46))
    palette.setColor(QPalette.ToolTipBase, QColor(205, 214, 244))
    palette.setColor(QPalette.ToolTipText, QColor(205, 214, 244))
    palette.setColor(QPalette.Text, QColor(205, 214, 244))
    palette.setColor(QPalette.Button, QColor(49, 50, 68))
    palette.setColor(QPalette.ButtonText, QColor(205, 214, 244))
    palette.setColor(QPalette.BrightText, QColor(255, 255, 255))
    palette.setColor(QPalette.Highlight, QColor(137, 180, 250))
    palette.setColor(QPalette.HighlightedText, QColor(30, 30, 46))
    app.setPalette(palette)

    window = MainWindow()
    window.show()
    
    # Windows 深色标题栏
    if sys.platform == 'win32':
        try:
            hwnd = int(window.winId())
            # 启用深色模式
            DWMWA_USE_IMMERSIVE_DARK_MODE = 20
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE,
                ctypes.byref(ctypes.c_int(1)), ctypes.sizeof(ctypes.c_int)
            )
            # 设置标题栏颜色为 #1e1e2e (RGB: 30, 30, 46)
            DWMWA_CAPTION_COLOR = 35
            color = 0x002E1E1E  # BGR格式: 0x00BBGGRR
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, DWMWA_CAPTION_COLOR,
                ctypes.byref(ctypes.c_int(color)), ctypes.sizeof(ctypes.c_int)
            )
        except:
            pass
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
