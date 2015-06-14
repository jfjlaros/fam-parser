"""
Tests for the python.fam_parser module.
"""


from fam_parser import FamParser


class TestParser(object):
    """
    Test the python.fam_parser module.
    """
    def setup(self):
        parser = FamParser(open('data/example.fam'))
        self.cleaned = parser.cleaned


    #def test_source(self):
    #    assert self.cleaned['source'] == 'Pedigree Editor V6.5'


    #def test_author(self):
    #    assert self.cleaned['family_drawn_by'] == 'Jeroen F.J. Laros'


    #def test_creation_date(self):
    #    assert self.cleaned['creation_date'] == '1111001'


    #def test_modification_date(self):
    #    assert self.cleaned['last_updated'] == '2222033'


    #def test_symbols_1(self):
    #    assert len(self.cleaned['genetic_symbols']) == 19


    #def test_symbols_2(self):
    #    assert len(self.cleaned['additional_symbols']) == 4


    #def test_symbols_3(self):
    #    assert len(self.cleaned['custom_symbols']) == 1


    #def test_symbols_4(self):
    #    assert self.cleaned['custom_symbols'][0]['name'] == 'custom symbol'


    #def test_symbols_5(self):
    #    assert self.cleaned['custom_symbols'][0]['value'] == 'AA'


    def test_family_id(self):
        assert self.cleaned['family']['id_number'] == '42'


    def test_family_name(self):
        assert self.cleaned['family']['name'] == 'Family Name'


    def test_comments(self):
        assert self.cleaned['family']['comments'] == 'Family related comments.'


    def test_family_disease_loci_1(self):
        assert len(self.cleaned['family']['disease_loci']) == 7


    def test_family_quantitative_value_loci(self):
        assert len(self.cleaned['family']['quantitative_value_loci']) == 7


    def test_members(self):
        assert len(self.cleaned['family']['members']) == 12


    def test_relationships(self):
        assert len(self.cleaned['family']['relationships']) == 4


    def test_relationship_member_1(self):
        assert self.cleaned['family']['relationships'][0]['members'][0] == 1


    def test_relationship_member_2(self):
        assert self.cleaned['family']['relationships'][0]['members'][1] == 2


    def test_relationship_consanguineous(self):
        assert self.cleaned['family']['relationships'][2]['consanguineous']


    def test_relationship_divorced(self):
        assert self.cleaned['family']['relationships'][1]['divorced']


    def test_relationship_informal(self):
        assert self.cleaned['family']['relationships'][2]['informal']
