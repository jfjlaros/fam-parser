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
        self.parsed = parser.parsed


    def test_source(self):
        assert self.parsed['source'] == 'Pedigree Editor V6.5'


    def test_author(self):
        assert self.parsed['family_drawn_by'] == 'Jeroen F.J. Laros'


    def test_creation_date(self):
        assert self.parsed['creation_date'] == '1111001'


    def test_modification_date(self):
        assert self.parsed['last_updated'] == '2222033'


    def test_symbols_1(self):
        assert len(self.parsed['genetic_symbols']) == 19


    def test_symbols_2(self):
        assert len(self.parsed['additional_symbols']) == 4


    def test_symbols_3(self):
        assert len(self.parsed['custom_symbols']) == 1


    def test_symbols_4(self):
        assert self.parsed['custom_symbols'][0]['name'] == 'custom symbol'


    def test_symbols_5(self):
        assert self.parsed['custom_symbols'][0]['value'] == 'AA'


    def test_family_id(self):
        assert self.parsed['id_number'] == '42'


    def test_family_name(self):
        assert self.parsed['name'] == 'Family Name'


    def test_comments(self):
        assert self.parsed['comments'] == 'Family related comments.'


    def test_family_disease_loci_1(self):
        assert len(self.parsed['disease_loci']) == 7


    def test_family_disease_loci_2(self):
        assert self.parsed['disease_loci'][3]['pattern'] == 'slanted_forward'


    def test_family_disease_loci_3(self):
        assert self.parsed['disease_loci'][3]['colour'] == '0x0000ff'


    def test_family_quantitative_value_loci(self):
        assert len(self.parsed['quantitative_value_loci']) == 7


    def test_members(self):
        assert len(self.parsed['members']) == 12


    def test_member_id(self):
        assert self.parsed['members'][0]['id'] == 1


    def test_member_individual_id(self):
        assert self.parsed['members'][0]['individual_id'] == '1'


    def test_member_forenames(self):
        assert self.parsed['members'][0]['forenames'] == 'Name1 Name2'


    def test_member_surname_1(self):
        assert self.parsed['members'][0]['surname'] == 'Surname'


    def test_member_surname_2(self):
        assert self.parsed['members'][1]['surname'] == 'Surname'


    def test_member_age_gestation(self):
        assert self.parsed['members'][0]['age_gestation'] == 'A/G text'


    def test_member_date_of_birth(self):
        assert self.parsed['members'][0]['date_of_birth'] == '1111001'


    def test_member_date_of_death(self):
        assert self.parsed['members'][0]['date_of_death'] == '2222033'


    def test_member_adoption_type(self):
        assert self.parsed['members'][0]['adoption_type'] == 'not_adopted'


    def test_member_gender(self):
        assert self.parsed['members'][0]['sex'] == 'male'


    def test_member_father_id_1(self):
        assert self.parsed['members'][0]['father_id'] == 0


    def test_member_father_id_2(self):
        assert self.parsed['members'][1]['father_id'] == 7


    def test_member_mother_id_1(self):
        assert self.parsed['members'][0]['mother_id'] == 0


    def test_member_mother_id_2(self):
        assert self.parsed['members'][1]['mother_id'] == 6


    def test_spouse_1(self):
        assert self.parsed['members'][0]['spouses'][0]['spouse_id'] == 2


    def test_spouse_2(self):
        assert self.parsed['members'][7]['spouses'][1]['spouse_id'] == 10


    def test_spouse_3(self):
        assert self.parsed['members'][5]['spouses'][0]['divorced']


    def test_spouse_4(self):
        assert self.parsed['members'][7]['spouses'][0]['consanguineous']


    def test_spouse_5(self):
        assert self.parsed['members'][7]['spouses'][0]['informal']


    #def test_relationships(self):
    #    assert len(self.parsed['relationships']) == 4


    #def test_relationship_member_1(self):
    #    assert self.parsed['relationships'][0]['members'][0] == 1


    #def test_relationship_member_2(self):
    #    assert self.parsed['relationships'][0]['members'][1] == 2


    #def test_relationship_consanguineous(self):
    #    assert self.parsed['relationships'][2]['consanguineous']


    #def test_relationship_divorced(self):
    #    assert self.parsed['relationships'][1]['divorced']


    #def test_relationship_informal(self):
    #    assert self.parsed['relationships'][2]['informal']
