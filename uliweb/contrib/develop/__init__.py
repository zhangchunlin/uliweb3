def dev_nav(active=None):
    from uliweb import settings

    out = "<ul>"
    for i in settings.MENUS_DEVELOP.nav:
        if active != i["name"]:
            out += "<li><a href='%s'>%s</a></li>" % (i["link"], i["title"])
        else:
            out += "<li class='active'><a href='%s'>%s</a></li>" % (i["link"], i["title"])
    out += "</ul>"
    return out
