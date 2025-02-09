import json

from PySide6.QtWidgets import QWidget

from interface.ui_search import Ui_Search
from qt_owner import QtOwner
from server import req, Log, Status
from server.sql_server import SqlServer
from task.qt_task import QtTaskBase
from tools.langconv import Converter
from tools.str import Str


class SearchView(QWidget, Ui_Search, QtTaskBase):
    def __init__(self, parent=None):
        QWidget.__init__(self, parent)
        Ui_Search.__init__(self)
        QtTaskBase.__init__(self)
        self.setupUi(self)
        self.isInit = False
        self.categories = ""
        self.text = ""
        self.isLocal = True
        self.isTitle = True
        self.isDes = True
        self.isCategory = True
        self.isTag = True
        self.isAuthor = True
        self.bookList.LoadCallBack = self.LoadNextPage
        self.categoryList.itemClicked.connect(self.ClickCategoryListItem)
        self.InitCategoryList()
        self.categoryList.setSelectionMode(self.categoryList.MultiSelection)
        self.categoryList.setSpacing(1)
        self.comboBox.currentIndexChanged.connect(self.ChangeSort)
        self.sortKey.currentIndexChanged.connect(self.ChangeSort)
        self.sortId.currentIndexChanged.connect(self.ChangeSort)
        self.searchButton.clicked.connect(self.lineEdit.Search)

    def InitWord(self):
        self.AddSqlTask("book", "", SqlServer.TaskTypeSelectWord, self.InitWordBack)
        self.lineEdit.SetCacheWord()
        return

    def InitWordBack(self, data):
        if not data:
            return
        self.lineEdit.SetWordData(data)

    def InitCategoryList(self):
        self.categoryList.clear()
        for name in ["耽美", "伪娘", "禁书", "扶她", "重口", "生肉", "纯爱", "WEBTOON"]:
            self.categoryList.AddItem(name, True)

    def SwitchCurrent(self, **kwargs):
        text = kwargs.get("text")
        self.categories = kwargs.get("categories", "")

        if self.categories:
            self.isLocal = False
            self.lineEdit.setText(self.categories)
            self.bookList.clear()
            self.SetEnable(self.isLocal)
            self.SendSearchCategories(1)
        elif text is not None:
            self.text = text
            self.lineEdit.setText(self.text)
            self.bookList.clear()
            isLocal = kwargs.get("isLocal")

            if isLocal is not None:
                self.isLocal = isLocal
            self.SetEnable(self.isLocal)
            self.isTitle = kwargs.get("isTitle")
            self.isDes = kwargs.get("isDes")
            self.isCategory = kwargs.get("isCategory")
            self.isTag = kwargs.get("isTag")
            self.isAuthor = kwargs.get("isAuthor")
            self.lineEdit.AddCacheWord(self.text)
            self.SendSearch(1)
        pass

    def SetDbError(self):
        self.isLocal = False
        self.SetEnable(False)
        self.lineEdit.SetDbError()

    def SetEnable(self, isLocal):
        self.sortId.setVisible(isLocal)
        self.sortKey.setVisible(isLocal)
        self.comboBox.setVisible(not isLocal)

    def SendSearchCategories(self, page):
        sort = ["dd", "da", "ld", "vd"]
        QtOwner().ShowLoading()
        sortId = sort[self.comboBox.currentIndex()]
        self.AddHttpTask(req.CategoriesSearchReq(page, self.categories, sortId), self.SendSearchBack)

    def SendSearchBack(self, raw):
        QtOwner().CloseLoading()
        try:
            self.bookList.UpdateState()
            data = json.loads(raw["data"])
            st = raw["st"]
            if st == Status.Ok:
                info = data.get("data").get("comics")
                page = int(info.get("page"))
                pages = int(info.get("pages"))
                self.bookList.UpdatePage(page, pages)
                self.spinBox.setValue(page)
                self.spinBox.setMaximum(pages)
                pageText = Str.GetStr(Str.Page) + ": " + str(self.bookList.page) + "/" + str(self.bookList.pages)
                self.label.setText(pageText)
                for v in info.get("docs", []):
                    self.bookList.AddBookByDict(v)
                self.CheckCategoryShowItem()
            else:
                # QtWidgets.QMessageBox.information(self, '未搜索到结果', "未搜索到结果", QtWidgets.QMessageBox.Yes)
                QtOwner().ShowError(Str.GetStr(st))
        except Exception as es:
            Log.Error(es)
        pass

    def SendSearch(self, page):
        QtOwner().ShowLoading()
        if self.isLocal:
            sql = SqlServer.Search(self.text, self.isTitle, self.isAuthor, self.isDes, self.isTag, self.isCategory, False, page, self.sortKey.currentIndex(), self.sortId.currentIndex())
            self.AddSqlTask("book", sql, SqlServer.TaskTypeSelectBook, callBack=self.SendLocalBack, backParam=page)
        else:
            sort = ["dd", "da", "ld", "vd"]
            sortId = sort[self.comboBox.currentIndex()]
            self.AddHttpTask(req.AdvancedSearchReq(page, [], self.text, sortId), self.SendSearchBack)

    def SendLocalBack(self, books, page):
        QtOwner().CloseLoading()
        self.bookList.UpdateState()
        pages = 100
        self.bookList.UpdatePage(page, pages)
        # self.jumpLine.setValidator(QtIntLimit(1, pages, self))
        self.spinBox.setValue(page)
        self.spinBox.setMaximum(pages)
        pageText = Str.GetStr(Str.Page) + ": " + str(self.bookList.page) + "/" + str(self.bookList.pages)
        self.label.setText(pageText)
        for v in books:
            self.bookList.AddBookItemByBook(v)
        self.CheckCategoryShowItem()

    def ClickCategoryListItem(self, item):
        # isClick = self.categoryList.ClickItem(item)
        # item = self.categoryList.itemFromIndex(index)
        data = item.text()
        if item.isSelected():
            QtOwner().ShowMsg(Str.GetStr(Str.Hidden) + data)
        else:
            QtOwner().ShowMsg(Str.GetStr(Str.NotHidden) + data)
        self.CheckCategoryShowItem()

    def CheckCategoryShowItem(self):
        data = []
        for i in range(self.categoryList.count()):
            item = self.categoryList.item(i)
            if item.isSelected():
                data.append(item.text())
        # data = self.categoryList.GetAllSelectItem()
        for i in range(self.bookList.count()):
            item = self.bookList.item(i)
            widget = self.bookList.itemWidget(item)
            isHidden = False
            text = widget.categoryLabel.text()
            text2 = Converter('zh-hans').convert(text)
            for name in data:
                if name in text2:
                    item.setHidden(True)
                    isHidden = True
                    break
            if not isHidden:
                item.setHidden(False)

    def JumpPage(self):
        page = int(self.spinBox.text())
        if page > self.bookList.pages:
            return
        self.bookList.page = page
        self.bookList.clear()
        if not self.categories:
            self.SendSearch(page)
        else:
            self.SendSearchCategories(page)
        return

    def LoadNextPage(self):
        if not self.categories:
            self.SendSearch(self.bookList.page + 1)
        else:
            self.SendSearchCategories(self.bookList.page + 1)
        return

    def ChangeSort(self, pos):
        self.bookList.page = 1
        self.bookList.clear()
        if not self.categories:
            self.SendSearch(1)
        else:
            self.SendSearchCategories(1)

    # def OpenSearchCategories(self, categories):
    #     # self.setFocus()
    #     # self.bookList.clear()
    #     self.categories = categories
    #     self.searchEdit.setPlaceholderText(categories)
    #     self.bookList.UpdatePage(1, 1)
    #     self.bookList.UpdateState()
    #     self.SendSearchCategories(1)