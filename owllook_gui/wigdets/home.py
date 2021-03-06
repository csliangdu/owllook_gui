#!/usr/bin/env python
"""
 Created by howie.hu at 2018/5/23.
"""
import asyncio

from bs4 import BeautifulSoup
from PyQt5 import QtCore, QtGui, QtWidgets

from owllook_gui.owl_resource import *
from owllook_gui.config import Config
from owllook_gui.database import books, engine, sql_delete_item, sql_get_all_result, sql_update_item
from owllook_gui.spider import get_novels_info, get_latest_chapter

from owllook_gui.wigdets import About, Search, SystemTray, table_widget_item_center, load_style_sheet

MAC = hasattr(QtGui, "qt_mac_set_native_menubar")


class OwlHome(QtWidgets.QMainWindow):

    def __init__(self, event_loop=None, parents=None):
        super(OwlHome, self).__init__(parent=parents)
        self.icon_path = Config.ICO_PATH
        self.system_tray_ins = SystemTray(parent=self)
        self.event_loop = event_loop if event_loop else asyncio.get_event_loop()
        self.engine = engine

        self.system_tray_ins.show()
        self.init_ui()

    def init_ui(self):
        # 加载样式
        load_style_sheet(self, 'main')
        # 设置图标以及标题
        self.setWindowTitle(Config.APP_TITLE)
        self.setWindowIcon(QtGui.QIcon(self.icon_path))

        # 检查更新
        self.func_refresh(refresh=True)

    def set_layout(self):
        # 布局
        self.v_box = QtWidgets.QVBoxLayout()
        self.v_box.addStretch()
        self.v_box.addWidget(self.middle_widget)
        self.v_box.addStretch()

        self.btn_search_book = QtWidgets.QPushButton("搜书")
        self.btn_refresh = QtWidgets.QPushButton("刷新")
        self.btn_about = QtWidgets.QPushButton("关于")

        self.btn_search_book.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        self.btn_refresh.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        self.btn_about.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))

        self.btn_search_book.clicked.connect(self.func_search)
        self.btn_refresh.clicked.connect(lambda: self.func_refresh(refresh=True))
        self.btn_about.clicked.connect(self.func_about)

        self.h_box = QtWidgets.QHBoxLayout()
        self.h_box.addWidget(self.btn_search_book)
        self.h_box.addWidget(self.btn_refresh)
        self.h_box.addWidget(self.btn_about)

        self.v_box.addLayout(self.h_box)

        main_frame = QtWidgets.QWidget()
        main_frame.setObjectName('home')
        main_frame.setLayout(self.v_box)
        self.setCentralWidget(main_frame)

    def func_about(self):
        """
        项目关于界面
        :return:
        """
        self.about_ins = About()
        self.about_ins.setWindowIcon(QtGui.QIcon(self.icon_path))
        self.about_ins.show()

    def func_check_version(self):
        pass

    def func_generate_menu(self, pos):
        row_num = -1
        for i in self.table_widget.selectionModel().selection().indexes():
            row_num = i.row()

        menu = QtWidgets.QMenu()
        delete_item = menu.addAction("删除")
        action = menu.exec_(self.table_widget.mapToGlobal(pos))

        if action == delete_item:
            # 获取某行数据
            title = self.table_widget.item(row_num, 0).text()
            url_str = self.table_widget.cellWidget(row_num, 1).text()
            soup = BeautifulSoup(url_str, 'html.parser')
            url = soup.find('a').get('href')

            values = {
                'title': title,
                'url': url
            }

            async def async_delete_item(self):
                await sql_delete_item(table_ins=books, engine=self.engine, values=values)
                self.func_refresh(refresh=False)

            self.event_loop.create_task(async_delete_item(self))

    def func_refresh(self, refresh=True):
        """
        刷新最新章节
        :return:
        """

        async def async_get_books(self, refresh):

            # Config.LOGGER.info('刷新数据成功')
            result = await sql_get_all_result(table_name='books', engine=self.engine)

            if result:
                # 表格布局
                self.table_widget = QtWidgets.QTableWidget()
                self.table_widget.clear()
                self.table_widget.setColumnCount(3)
                self.table_widget.setRowCount(len(result))
                self.table_widget.setObjectName('books_table')
                # 表格100%填满窗口
                self.table_widget.horizontalHeader().setStretchLastSection(True)
                self.table_widget.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
                # 设置选中表格整行
                self.table_widget.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
                # 设置表格不可编辑
                self.table_widget.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
                # 设置字体
                # self.table_widget.setFont(QtGui.QFont('SansSerif', 12))

                self.table_widget.setHorizontalHeaderLabels(["小说名", "目录", "最新章节"])

                for index, each in enumerate(result):
                    if refresh:
                        latest_chapter_name, latest_chapter_url = await get_latest_chapter(each[2])
                        if not latest_chapter_name or not latest_chapter_url:
                            latest_chapter_name, latest_chapter_url = each[3], each[4]
                        if each[3] != latest_chapter_name:
                            # 需要更新数据库
                            condition = {
                                'title': each[1],
                                'url': each[2]
                            }
                            values = {
                                'latest_chapter_name': latest_chapter_name,
                                'latest_chapter_url': latest_chapter_url
                            }

                            await sql_update_item(table='books',
                                                  engine=self.engine,
                                                  condition=condition,
                                                  values=values)
                    else:
                        latest_chapter_name, latest_chapter_url = each[3], each[4]

                    self.table_widget.setItem(index, 0, table_widget_item_center(each[1]))
                    label_chapter = QtWidgets.QLabel("<a href='{}'>查看目录</a>".format(each[2]))
                    label_chapter.setToolTip(each[2])
                    label_chapter.setOpenExternalLinks(True)
                    label_chapter.setObjectName('lable_chapter')
                    label_chapter.setAlignment(QtCore.Qt.AlignCenter)
                    self.table_widget.setCellWidget(index, 1, label_chapter)

                    label_latest_chapter = QtWidgets.QLabel(
                        "<a href='{}'>{}</a>".format(latest_chapter_url, latest_chapter_name))
                    label_latest_chapter.setOpenExternalLinks(True)
                    label_latest_chapter.setObjectName('lable_chapter')
                    label_latest_chapter.setAlignment(QtCore.Qt.AlignCenter)
                    self.table_widget.setCellWidget(index, 2, label_latest_chapter)

                self.middle_widget = self.table_widget
                # 右键菜单
                self.table_widget.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
                self.table_widget.customContextMenuRequested.connect(self.func_generate_menu)
                self.resize(485, 250)
            else:
                self.bookshelf = QtWidgets.QLabel('书架暂无数据')
                self.bookshelf.setObjectName('bookshelf')
                self.bookshelf.setAlignment(QtCore.Qt.AlignCenter)
                self.middle_widget = self.bookshelf
                self.resize(350, 250)

            self.set_layout()
            self.func_win_center()
            if not self.isVisible():
                self.show()

        self.event_loop.create_task(async_get_books(self, refresh))

    def func_search(self):
        """
        小说检索
        :return:
        """
        self.search_ins = Search(self)
        self.search_ins.setWindowIcon(QtGui.QIcon(self.icon_path))
        self.search_ins.show()

    def func_win_center(self):
        screen = QtWidgets.QDesktopWidget().screenGeometry()
        size = self.geometry()
        self.move((screen.width() - size.width()) / 2, (screen.height() - size.height()) / 2)

    def closeEvent(self, event):
        self.hide()
        event.ignore()


if __name__ == '__main__':
    import sys

    app = QtWidgets.QApplication(sys.argv)
    # 关闭所有窗口也不关闭应用程序
    # QApplication.setQuitOnLastWindowClosed(False)
    win = OwlHome()

    win.show()
    sys.exit(app.exec_())
