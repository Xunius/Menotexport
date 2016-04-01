'''Fix error words extracted from highlights.

It seems that the combinations "fl" and "fi" mostly fail from text extraction by
pdfminer. E.g. 'first', 'flux', 'deficiency' will be u'\ufb01rst', 
u'\ufb02ux' and u'de\ufb01ciency'.



# Copyright 2016 Guang-zhi XU
#
# This file is distributed under the terms of the
# GPLv3 licence. See the LICENSE file for details.
# You may use, distribute and modify this code under the
# terms of the GPLv3 license.

Update time: 2016-04-01 16:00:57.
'''


import re


_tilder_re=re.compile(u'\u02dc', re.UNICODE)
_fl_re=re.compile(u'\ufb02', re.UNICODE)
_fi_re=re.compile(u'\ufb01', re.UNICODE)
_ft_re=re.compile(u'\ufb05', re.UNICODE)
_single_quote_re=re.compile(u'\u2019', re.UNICODE)
_single_dash_re=re.compile(u'\u2013', re.UNICODE)

KNOWN_LIST={\
        _tilder_re: u'',\
        _fl_re: u'fl',\
        _fi_re: u'fi',\
        _ft_re: u'ft',\
        _single_quote_re: u"'",\
        _single_dash_re: u'-'\
        }


def fixWord(text):
    for reii,replaceii in KNOWN_LIST.items():
        text=reii.sub(replaceii,text)

    return text







