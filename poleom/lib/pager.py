"""Pager class."""


class Pager:
    """Pager object."""
    # pylint: disable=too-many-instance-attributes

    def __init__(self, offset=0, limit=10, order="", sort="asc"):
        self.d_offset = offset
        self.d_limit = limit
        self.d_order = order
        self.d_sort = sort

        self.offset = offset
        self.limit = limit
        self.order = order
        self.sort = sort
        self.total = 0

        self.params = ""

    @property
    def pages(self):
        """Return count of pages."""
        return int((self.total - 1) / self.limit)

    @property
    def page(self):
        """Return acutal page number."""
        return int(self.offset / self.limit)

    @property
    def last(self):
        """Return offset for last page"""
        return self.limit * self.pages

    def bind(self, form):
        """Bind variables from Request.Args or Request.Form."""
        self.offset = form.getfirst("offset", self.offset, int)
        self.limit = form.getfirst("limit", self.limit, int)
        self.order = form.getfirst("order", self.order, str)

        sort = form.getfirst("sort", self.sort, str)
        self.sort = sort if sort in ("asc", "desc") else self.sort

    def set_params(self, **kwargs):
        """Set specific query arguments."""
        self.params = "&".join(f"{key}={val}"
                               for key, val in kwargs.items())

    def sql_dict(self):
        """Return dictionary for SQL"""
        return {"OFFSET": self.offset,
                "LIMIT": self.limit}
