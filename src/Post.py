import OrcFxAPI as orca
import numpy as np
import matplotlib.pyplot as pyplot
import pandas as pd


class Post:

    def __init__(self) -> None:
        self.results = {
            'statics': pd.DataFrame(),
            'modal': pd.DataFrame,
            'dynamics': pd.DataFrame()
        }

        self.period: any
        self.to_plot: dict
        self.formats: dict

    def set_options(self, input_definitions: dict) -> None:
        """Define options and simulation period to plot and/or export

        Args:
            input_definitions (dict): [description]
        """

        self.to_plot = input_definitions['plot']
        self.formats = input_definitions['export format']
        self.period = self.set_result_period(input_definitions.get('period'))

    def process_results(self, options: dict, lines, platforms,
                        towers=None, turbines=None, nacelles=None) -> None:

        self.results['dynamics']["Time"] = platforms[1].SampleTimes(
            self.period)

        if options.get('lines'):
            # Tensions
            for cur_line_definition in options['lines']:
                # Line ID number
                num = cur_line_definition['id']

                # Check if static tension is requested
                if 'static' in cur_line_definition:
                    self.results['statics']['tension'] = \
                        lines[num].RangeGraph(
                            'Effective tension', period=orca.pnStaticState)

                if cur_line_definition.get('tension'):
                    self.process_line_tension(
                        cur_line_definition['tension'], lines[num], num
                    )
            # Motion
            for cur_line_definition in options['lines']:
                # Line ID number
                num = cur_line_definition['id']

                if cur_line_definition.get('motion'):
                    self.process_line_motion(
                        cur_line_definition['motion'], lines[num], num
                    )

        # if options.get('platforms'):
         #     for cur_def in options['platforms']:
         #         # Platform ID number
         #         num = cur_def['id']
         #         # Current Orcaflex vessel object
         #         plat = platforms[num]

    def process_line_tension(self, points, line, line_id) -> None:
        # points: dict | string
        if isinstance(points, str) and points == 'all nodes':
            tot_nodes = len(line.NodeArclengths)
            for node in range(1, tot_nodes+1):
                # Set name of DataFrame column
                if node == 1:
                    node_id = "A_Tension"
                elif node == tot_nodes:
                    node_id = "B_Tension"
                else:
                    node_id = str(node) + "_Tension"
                col_name = "Line" + str(line_id) + "_Node" + node_id

                # self.results[col_name] = line.TimeHistory(
                self.results['dynamics'][col_name] = line.TimeHistory(
                    'Effective tension', self.period, orca.oeNodeNum(node)
                )

            return None

        if 'fairleads' in points:
            predicate = "Line" + str(line_id)
            if 'A' in points['fairleads']:
                self.results['dynamics'][predicate + "_NodeA_Tension"] = \
                    line.TimeHistory(
                        'Effective tension', self.period, orca.oeEndA
                )
            # If is not anchored, the line has 2 fairleads
            if 'B' in points['fairleads'] and line.EndBConnection != 'Anchored':
                self.results['dynamics'][predicate + "_NodeB_Tension"] = \
                    line.TimeHistory(
                    'Effective tension', self.period, orca.oeEndB
                )

        if 'end segments' in points:
            if points['end segments'] == 'all':
                first, last = 0, line.NumberOfSections - 1
            else:
                first, last = points['end segments']

            for seg in range(first, last, 1):
                self.results['dynamics']["Line" + str(line_id) + "_EndSeg" +
                                         str(seg + 1) + "_Tension"] = \
                    line.TimeHistory(
                    'Effective tension', self.period,
                    orca.oeArcLength(line.CumulativeLength[seg])
                )

        if 'arc length' in points:
            for arc_len in points['arc length']:
                self.results['dynamics']["Line" + str(line_id) + "_ArcLen" +
                                         str(arc_len) + "_Tension"] = \
                    line.TimeHistory(
                        'Effective tension', self.period,
                    orca.oeArcLength(line.CumulativeLength[seg])
                )

    def process_line_motion(self, points: dict, line, line_id) -> None:
        if 'all nodes' in points:
            tot_nodes = len(line.NodeArclengths)

            # Define DoFs to monitor
            if points['all nodes'] == 'all dofs':
                dofs = 'X', 'Y', 'Z', \
                    'Dynamic Rx', 'Dynamic Ry', 'Dynamic Rz'
            else:
                dofs = tuple(points['all nodes'])

            # Iterate nodes
            for node in range(1, tot_nodes+1):
                # Set name of DataFrame column
                if node == 1:
                    node_id = "A"
                elif node == tot_nodes:
                    node_id = "B"
                else:
                    node_id = str(node)
                col_name = "Line" + str(line_id) + "_Node" + node_id + "_"

                # Iterate DoFs and push to DataFrame
                for dof in dofs:
                    self.results['dynamics'][col_name + dof.replace(" ", "")] = \
                        line.TimeHistory(
                            dof, self.period, orca.oeNodeNum(node)
                    )

            return None

        if 'fairleads' in points:
            for node, definition in points['fairleads'].items():
                predicate = "Line" + str(line_id) + "_Node" + node

                # Define DoFs to monitor
                if definition['dofs'] == 'all':
                    dofs = 'X', 'Y', 'Z', \
                        'Dynamic Rx', 'Dynamic Ry', 'Dynamic Rz'
                    # 'Rotation 1', 'Rotation 2', 'Rotation 3'
                else:
                    dofs = tuple(points['fairleads'][node]['dofs'])

                # Check which fairlead (in case of a shared line)
                if node == 'A':
                    end_node = orca.oeEndA
                else:
                    end_node = orca.oeEndB

                for dof in dofs:
                    # Remove spaces in Rotations
                    self.results['dynamics'][predicate + "_" + dof.replace(" ", "")] = \
                        line.TimeHistory(
                        dof, self.period, end_node
                    )

        if 'end segments' in points:
            # Define segments to monitor
            if points['end segments']['ids'] == 'all':
                segments = range(0, line.NumberOfSections - 1, 1)
            else:
                segments = points['end segments']['ids']

            # Define DoFs to monitor
            if points['end segments']['dofs'] == 'all':
                dofs = 'X', 'Y', 'Z', \
                    'Dynamic Rx', 'Dynamic Ry', 'Dynamic Rz'
                # 'Rotation 1', 'Rotation 2', 'Rotation 3'
            else:
                dofs = tuple(points['end segments']['dofs'])

            # Push results to results DataFrame
            for seg in segments:
                predicate = "Line" + str(line_id) + "_EndSeg" + str(seg + 1)

                for dof in dofs:
                    self.results['dynamics'][predicate + "_" + dof.replace(" ", "")] = \
                        line.TimeHistory(
                            dof, self.period,
                            orca.oeArcLength(line.CumulativeLength[seg])
                    )

        if 'arc length' in points:
            for arc_len, definition in points['arc length'].items():
                predicate = "Line" + str(line_id) + "_ArcLen" + str(arc_len)

                # Define DoFs to monitor
                if definition['dofs'] == 'all':
                    dofs = 'X', 'Y', 'Z', \
                        'Dynamic Rx', 'Dynamic Ry', 'Dynamic Rz'
                    # 'Rotation 1', 'Rotation 2', 'Rotation 3'
                else:
                    dofs = tuple(points['arc length'][node]['dofs'])

                # Push results to results DataFrame
                for dof in dofs:
                    # dof_ = dof.replace(" ", "")  # remove space (rotation)
                    self.results['dynamics'][predicate + "_" + dof.replace(" ", "")] = \
                        line.TimeHistory(
                            dof, self.period,
                            orca.oeArcLength(float(arc_len))
                    )
            ####################################

    def set_result_period(self, definitions):
        if definitions is None or definitions == 'whole simulation':
            return orca.SpecifiedPeriod(orca.pnWholeSimulation)
        if definitions.get('stage'):
            return definitions.get('stage') - 1
        if definitions.get('specified'):
            return orca.SpecifiedPeriod(definitions['specified'][0],
                                        definitions['specified'][1])
