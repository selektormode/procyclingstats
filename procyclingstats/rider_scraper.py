import calendar
from typing import Any, Dict, List

from .scraper import Scraper
from .table_parser import TableParser
from .utils import (format_regex_str, get_day_month, parse_table_fields_args,
                    reg)


class Rider(Scraper):
    """Scraper for rider HTML page. Example URL: ``rider/tadej-pogacar``."""
    _url_validation_regex = format_regex_str(
    f"""
        {reg.base_url}?rider
        {reg.url_str}({reg.overview}{reg.anything}?|
        {reg.year}{reg.anything}?)?
        \\/*
    """)
    """Regex for validating rider URL."""

    def normalized_relative_url(self) -> str:
        """
        Creates normalized relative URL. Determines equality of objects (is
        used in __eq__ method).

        :return: Normalized URL in ``rider/{rider_id}`` format.
        """
        decomposed_url = self._decompose_url()
        rider_id = decomposed_url[1]
        return f"rider/{rider_id}"

    def birthdate(self) -> str:
        """
        Parses rider's birthdate from HTML.

        :return: birthday of the rider in ``YYYY-MM-DD`` format.
        """
        general_info_html = self.html.css_first(".rdr-info-cont")
        bd_string = general_info_html.text(separator=" ", deep=False)
        bd_list = [item for item in bd_string.split(" ") if item][:3]
        [day, str_month, year] = bd_list
        month = list(calendar.month_name).index(str_month)
        return f"{year}-{month}-{day}"

    def place_of_birth(self) -> str:
        """
        Parses rider's place of birth from HTML

        :return: rider's place of birth (town only).
        """
        # normal layout
        try:
            place_of_birth_html = self.html.css_first(
                ".rdr-info-cont > span > span > a")
            return place_of_birth_html.text()
        # special layout
        except AttributeError:
            place_of_birth_html = self.html.css_first(
                ".rdr-info-cont > span > span > span > a")
            return place_of_birth_html.text()

    def name(self) -> str:
        """
        Parses rider's name from HTML.

        :return: Rider's name.
        """
        return self.html.css_first(".page-title > .main > h1").text()

    def weight(self) -> int:
        """
        Parses rider's current weight from HTML.

        :return: Rider's weigth in kilograms.
        """
        # normal layout
        try:
            weight_html = self.html.css(".rdr-info-cont > span")[1]
            return int(weight_html.text().split(" ")[1])
        # special layout
        except (AttributeError, IndexError):
            weight_html = self.html.css(".rdr-info-cont > span > span")[1]
            return int(weight_html.text().split(" ")[1])

    def height(self) -> float:
        """
        Parses rider's height from HTML.

        :return: Rider's height in meters.
        """
        # normal layout
        try:
            height_html = self.html.css_first(".rdr-info-cont > span > span")
            return float(height_html.text().split(" ")[1])
        # special layout
        except (AttributeError, IndexError):
            height_html = self.html.css_first(
                ".rdr-info-cont > span > span > span")
            return float(height_html.text().split(" ")[1])

    def nationality(self) -> str:
        """
        Parses rider's nationality from HTML.

        :return: Rider's current nationality as 2 chars long country code in
            uppercase.
        """
        # normal layout
        nationality_html = self.html.css_first(".rdr-info-cont > .flag")
        if nationality_html is None:
        # special layout
            nationality_html = self.html.css_first(
                ".rdr-info-cont > span > span")
        flag_class = nationality_html.attributes['class']
        return flag_class.split(" ")[-1].upper() # type:ignore


    def teams_history(self, *args: str) -> List[Dict[str, Any]]:
        """
        Parses rider's team history throughout career.

        :param args: Fields that should be contained in returned table. When
            no args are passed, all fields are parsed.

            - team_name:
            - team_url:
            - season:
            - class: Team's class, e.g. ``WT``.
            - since: First day for rider in current season in the team in
              ``MM-DD` format, most of the time ``01-01``.
            - until: Last day for rider in current season in the team in
              ``MM-DD` format, most of the time ``12-31``.

        :raises ValueError: When one of args is of invalid value.
        :return: Table with wanted fields.
        """
        available_fields = (
            "season",
            "since",
            "until",
            "team_name",
            "team_url",
            "class"
        )
        fields = parse_table_fields_args(args, available_fields)
        seasons_html_table = self.html.css_first("ul.list.rdr-teams")
        table_parser = TableParser(seasons_html_table)
        casual_fields = [f for f in fields
                         if f in ("season", "team_name", "team_url")]
        if casual_fields:
            table_parser.parse(casual_fields)
        # add classes for row validity checking
        classes = table_parser.parse_extra_column(2,
            lambda x: x.replace("(", "").replace(")", "").replace(" ", "")
            if x and "retired" not in x else None)
        table_parser.extend_table("class", classes)
        if "since" in fields:
            until_dates = table_parser.parse_extra_column(-2,
                lambda x: get_day_month(x) if "as from" in x else "01-01")
            table_parser.extend_table("since", until_dates)
        if "until" in fields:
            until_dates = table_parser.parse_extra_column(-2,
                lambda x: get_day_month(x) if "until" in x else "12-31")
            table_parser.extend_table("until", until_dates)

        table = [row for row in table_parser.table if row['class']]
        # remove class field if isn't needed
        if "class" not in fields:
            for row in table:
                row.pop("class")
        return table

    def points_per_season_history(self, *args: str) -> List[Dict[str, Any]]:
        """
        Parses rider's points per season history.

        :param args: Fields that should be contained in returned table. When
            no args are passed, all fields are parsed.

            - season:
            - points: PCS points gained throughout the season.
            - rank: PCS ranking position after the season.

        :raises ValueError: When one of args is of invalid value.
        :return: Table with wanted fields.
        """
        available_fields = (
            "season",
            "points",
            "rank"
        )
        fields = parse_table_fields_args(args, available_fields)
        points_table_html = self.html.css_first("table.rdr-season-stats")
        table_parser = TableParser(points_table_html)
        table_parser.parse(fields)
        return table_parser.table
