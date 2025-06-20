from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged('post_install', '-at_install')
class TestResCurrency(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.env.ref('base.lang_uk_UA').active = True
        context = dict(cls.env.context)
        context['lang'] = 'uk_UA'
        cls.env = cls.env(context=context)

        cls.currency_uah = cls.env.ref('base.UAH')
        cls.currency_usd = cls.env.ref('base.USD')
        cls.currency_eur = cls.env.ref('base.EUR')

    def test_amount_to_text(self):
        self.assertEqual(self.currency_uah.amount_to_text(23), 'двадцять три гривні, нуль копійок')
        self.assertEqual(self.currency_uah.amount_to_text(11.3), 'одинадцять гривень, тридцять копійок')
        self.assertEqual(self.currency_uah.amount_to_text(10.333333), 'десять гривень, тридцять три копійки')
        self.assertEqual(self.currency_uah.amount_to_text(10.666666), 'десять гривень, шістдесят сім копійок')
        self.assertEqual(self.currency_uah.amount_to_text(999100222), 'дев\'ятсот дев\'яносто дев\'ять мільйонів сто тисяч двісті двадцять дві гривні, нуль копійок')
        self.assertEqual(self.currency_uah.amount_to_text(0), '')
        self.assertEqual(self.currency_uah.amount_to_text(0.01), 'нуль гривень, одна копійка')
        self.assertEqual(self.currency_usd.amount_to_text(-1), 'мінус один долар, нуль центів')
        self.assertEqual(self.currency_eur.amount_to_text(-24.32), 'мінус двадцять чотири євро, тридцять два центи')
