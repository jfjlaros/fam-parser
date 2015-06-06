"""
Tests for the python.fam_parser module.
"""


from fam_parser import FamParser


class TestParser(object):
    """
    Test the python.fam_parser module.
    """
    def setup(self):
        parser = FamParser()
        parser.read(open('data/example.fam'))
        self.parsed = parser.parsed


    def test_source(self):
        assert self.parsed['METADATA']['SOURCE'] == 'Pedigree Editor V6.5'


    def test_author(self):
        assert (self.parsed['METADATA']['FAMILY_DRAWN_BY'] ==
            'Jeroen F.J. Laros')


    def test_creation_date(self):
        assert self.parsed['METADATA']['CREATION_DATE'] == '1111001'


    def test_modification_date(self):
        assert self.parsed['METADATA']['LAST_UPDATED'] == '2222033'


    def test_symbols_1(self):
        assert len(self.parsed['METADATA']['GENETIC_SYMBOLS']) == 19


    def test_symbols_2(self):
        assert len(self.parsed['METADATA']['ADDITIONAL_SYMBOLS']) == 5


    def test_symbols_3(self):
        assert (self.parsed['METADATA']['ADDITIONAL_SYMBOLS'][4]['NAME'] ==
            'custom symbol')


    def test_symbols_4(self):
        assert (self.parsed['METADATA']['ADDITIONAL_SYMBOLS'][4]['VALUE'] ==
            'AA')


    def test_family_id(self):
        assert self.parsed['FAMILY']['ID_NUMBER'] == '42'


    def test_family_name(self):
        assert self.parsed['FAMILY']['NAME'] == 'Family Name'


    def test_comments(self):
        assert self.parsed['FAMILY']['COMMENTS'] == 'Family related comments.'


    def test_family_disease_loci_1(self):
        assert len(self.parsed['FAMILY']['DISEASE_LOCI']) == 7


    def test_family_disease_loci_2(self):
        assert (self.parsed['FAMILY']['DISEASE_LOCI'][3]['PATTERN'] ==
            'SLANTED_FORWARD')


    def test_family_disease_loci_3(self):
        assert (self.parsed['FAMILY']['DISEASE_LOCI'][3]['COLOUR'] ==
            '0x0000ff')


    def test_family_quantitative_value_loci(self):
        assert len(self.parsed['FAMILY']['QUANTITATIVE_VALUE_LOCI']) == 7


    def test_members(self):
        assert len(self.parsed['FAMILY']['MEMBERS']) == 12


    def test_member_id(self):
        assert self.parsed['FAMILY']['MEMBERS'][0]['ID'] == 1


    def test_member_individual_id(self):
        assert self.parsed['FAMILY']['MEMBERS'][0]['INDIVIDUAL_ID'] == '1'


    def test_member_forenames(self):
        assert (self.parsed['FAMILY']['MEMBERS'][0]['FORENAMES'] ==
            'Name1 Name2')


    def test_member_surname_1(self):
        assert self.parsed['FAMILY']['MEMBERS'][0]['SURNAME'] == 'Surname'


    def test_member_surname_2(self):
        assert self.parsed['FAMILY']['MEMBERS'][1]['SURNAME'] == 'Surname'


    def test_member_age_gestation(self):
        assert (self.parsed['FAMILY']['MEMBERS'][0]['AGE_GESTATION'] ==
            'A/G text')


    def test_member_date_of_birth(self):
        assert (self.parsed['FAMILY']['MEMBERS'][0]['DATE_OF_BIRTH'] ==
            '1111001')


    def test_member_date_of_death(self):
        assert (self.parsed['FAMILY']['MEMBERS'][0]['DATE_OF_DEATH'] ==
            '2222033')


    def test_member_adoption_type(self):
        assert (self.parsed['FAMILY']['MEMBERS'][0]['ADOPTION_TYPE'] ==
            'NOT_ADOPTED')


    def test_member_gender(self):
        assert self.parsed['FAMILY']['MEMBERS'][0]['SEX'] == 'MALE'


    def test_member_father_id_1(self):
        assert self.parsed['FAMILY']['MEMBERS'][0]['FATHER_ID'] == 0


    def test_member_father_id_2(self):
        assert self.parsed['FAMILY']['MEMBERS'][1]['FATHER_ID'] == 7


    def test_member_mother_id_1(self):
        assert self.parsed['FAMILY']['MEMBERS'][0]['MOTHER_ID'] == 0


    def test_member_mother_id_2(self):
        assert self.parsed['FAMILY']['MEMBERS'][1]['MOTHER_ID'] == 6


    def test_relationships(self):
        assert len(self.parsed['FAMILY']['RELATIONSHIPS']) == 4


    def test_relationship_member_1(self):
        assert self.parsed['FAMILY']['RELATIONSHIPS'][0]['MEMBERS'][0] == 1


    def test_relationship_member_2(self):
        assert self.parsed['FAMILY']['RELATIONSHIPS'][0]['MEMBERS'][1] == 2


    def test_relationship_consanguineous(self):
        assert (self.parsed['FAMILY']['RELATIONSHIPS'][2]['CONSANGUINEOUS'] ==
            True)


    def test_relationship_divorced(self):
        assert self.parsed['FAMILY']['RELATIONSHIPS'][1]['DIVORCED'] == True


    def test_relationship_informal(self):
        assert self.parsed['FAMILY']['RELATIONSHIPS'][2]['INFORMAL'] == True
