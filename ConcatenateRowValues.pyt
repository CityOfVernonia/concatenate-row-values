# -*- coding: utf-8 -*-

import arcpy
import collections
import locale
locale.setlocale(locale.LC_ALL, '')

def checkField(fromFieldType, toFieldType, delimiter):
    """A function to check for correct field types between the from and to fields."""

    if fromFieldType == "String":
        if not toFieldType == "String":
            arcpy.AddError("Copy To Field must be of type text when Read From Field is of type text.")
    else:
        if not toFieldType == "String":
            if delimiter != "":
                arcpy.AddError("Copy To Field must be of type text when Read From Field is of type numeric or date and you are using a delimiter.")

            if delimiter == "":
                if fromFieldType == "SmallInteger":
                    if not toFieldType in ["Integer",  "SmallInteger", "Float", "Double"]:
                        if toFieldType == "Date":
                            arcpy.AddError("Copy To Field must be of type text.")

                if fromFieldType == "Integer":
                    if toFieldType in ["SmallInteger", "Integer", "Float", "Double", "Date"]:
                        arcpy.AddError("Copy To Field must be of type text.")

                else:
                    if fromFieldType in ["Float", "Double" , "Date"]:
                        if toFieldType in ["Integer", "SmallInteger", "Float", "Double" , "Date"]:
                            arcpy.AddError("Copy To Field must be of type text.")

class Toolbox(object):
    def __init__(self):
        self.label = "Toolbox"
        self.alias = "toolbox"

        # List of tool classes associated with this toolbox
        self.tools = [ConcatenateRowValues]


class ConcatenateRowValues(object):
    def __init__(self):
        self.label = "Concatenate Row Values"
        self.description = "Concatenate row values for a specified field."
        self.canRunInBackground = False

    def getParameterInfo(self):
        inputTable = arcpy.Parameter(
            displayName="Input Table",
            name="inputTable",
            datatype=["GPFeatureLayer", "DETable", "GPTableView"],
            parameterType="Required",
            direction="Input")

        caseField = arcpy.Parameter(
            displayName="Case Field",
            name="caseField",
            datatype="Field",
            parameterType="Required",
            direction="Input")

        fromField = arcpy.Parameter(
            displayName="Read from Field",
            name="fromField",
            datatype="Field",
            parameterType="Required",
            direction="Input")

        toField = arcpy.Parameter(
            displayName="Copy to Field",
            name="toField",
            datatype="Field",
            parameterType="Required",
            direction="Input")

        delimiter = arcpy.Parameter(
            displayName="Delimiter",
            name="delimiter",
            datatype="GPString",
            parameterType="Optional",
            direction="Input")

        outputTable = arcpy.Parameter(
            displayName="Updated Table",
            name="outTable",
            datatype=["GPFeatureLayer", "DETable"],
            parameterType="Derived",
            direction="Output")

        caseField.parameterDependencies = [inputTable.name]
        fromField.parameterDependencies = [inputTable.name]
        toField.parameterDependencies = [inputTable.name]
        delimiter.value = ","
        outputTable.parameterDependencies = [inputTable.name]
        outputTable.schema.clone = True
        
        return [inputTable, caseField, fromField, toField, delimiter, outputTable]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):
        # Access parameters.
        inputTable = parameters[0].valueAsText
        caseField = parameters[1].valueAsText
        fromField = parameters[2].valueAsText
        toField = parameters[3].valueAsText
        delimiter = parameters[4].valueAsText

        # Get field types for from and to fields; and to field length.
        fromFieldType = arcpy.ListFields(inputTable, fromField)[0].type
        toFieldType = arcpy.ListFields(inputTable, toField)[0].type
        toFieldLength = arcpy.ListFields(inputTable, toField)[0].length

        # Check that the from and to fields match correctly for concatenation.
        checkField(fromFieldType, toFieldType, delimiter)

        # Create dictionary to store results.
        dictionary = collections.defaultdict(list)

        # Append case field dictionary key with from field values.
        try:
            srows = None
            srows = srows = arcpy.SearchCursor(inputTable, '', '', '', '{0} A;{1} A'.format(caseField, fromField))
            for row in srows:
                caseId = row.getValue(caseField)
                value = row.getValue(fromField)
                if fromField in ['Double', 'Float']:
                    value = locale.format('%s', (row.getValue(fromField)))
                if value != None:
                    dictionary[caseId].append(value)
        except RuntimeError as re:
            arcpy.AddError('Error in accessing {0}. {1}'.format(inputTable, re.args[0]))
        finally:
            if srows:
                del srows

        # Update each case field with concatenated from field values in dictionary.
        try:
            urows = None
            urows = arcpy.UpdateCursor(inputTable)
            for row in urows:
                caseId = row.getValue(caseField)
                values = dictionary[caseId]
                f = u''.join(str(val) for val in values)

                if not delimiter == '':
                    if (len(f) + (len(values)-1)) > toFieldLength:
                        arcpy.AddError('Length of the Copy to Field is less than the length of the content you are trying to copy.')
                    else:
                        if fromFieldType in ['String']:
                            if toFieldType in ['String']:
                                row.setValue(toField, delimiter.join(sorted(set([val for val in values if not value is None]))))
                        else:
                            row.setValue(toField, delimiter.join(sorted(set([str(val) for val in values if not value is None]))))
                else:
                    if toFieldType in ['String']:
                        if len(f) > toFieldLength:
                            arcpy.AddError('Length of the Copy to Field is less than the length of the content you are trying to copy.')
                    else:
                        if fromFieldType in ['String']:
                            if toFieldType in ['String']:
                                row.setValue(toField, delimiter.join(sorted(set([val for val in values if not value is None]))))
                        else:
                            if toFieldType in ['String']:
                                row.setValue(toField, delimiter.join(sorted(set([str(val) for val in values if not value is None]))))
                            elif toFieldType in ['Integer', 'SmallInteger'] :
                                row.setValue(toField, int(delimiter.join(sorted(set([str(val) for val in values if not val is None])))))
                            elif toFieldType in ['Double', 'Float']:
                                row.setValue(toField, float(delimiter.join(sorted(set([str(val) for val in values if not val is None])))))

                # Date formatting can be edited to match local.
                if fromFieldType in ['Date']:
                    row.setValue(sort(toField, delimiter.join([val.strftime('%d%m%Y') for val in values if not val is None])))
                urows.updateRow(row)

        except RuntimeError as re:
            arcpy.AddError('Error updating {0}. {1}'.format(inputTable, re.args[0]))
        finally:
            if urows:
                del urows

        return
