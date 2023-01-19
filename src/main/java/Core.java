import java.io.*;
import java.util.*;
import java.util.Map.Entry;


public class Core {
    static void init() throws Exception {
        Sim_App.append_to_text_area("Initializing SwarmEngine");
        Sim_App.set_properties_as_available(false);

        Sim_App.append_to_text_area("Preparing the Optimization Workers (number: " + Sim_App.threads + ")");
        MathEngine.create_the_optimizers();

        parse_db();
        // computeInitialCrossDistances();
        // Use this for debugging and to set the nodes to true Pos
        // reset_CurrentNodePos_to_TruePos();
        sort_nodes_by_popularity();

        // This is the first Map_Extent update to set the Global Min/Max X/Y to be ready for even the first optimization
        MapField.update_MapExtent();

        // Make a small benchmark comparing computational demands between Pure Java and Mathematica
        //compare_timings();
        Sim_App.set_properties_as_available(true);
        Sim_App.resumeBtn.setVisible(true);
    }

    static void get_the_effective_neighbors(Node currentNode) {

        // Find the closest remote Nodes to it
        Sim_App.effective_remoteNodes = new ArrayList<>();

        //Get the RSS values from all other Nodes
        for (HashMap.Entry<Integer, Double> entry : currentNode.measurement_from_node.entrySet()) {

            int remoteNode = entry.getKey();
            double measurement_value = entry.getValue();

            // Ignore all measurement values that are not described by our model
            // Todo: change sign according to measurement type
            //System.out.println("Checking if measurement " + measurement_value + " between remote Node " + remoteNode + " and current Node " + currentNode + " is at least " + Sim_App.min_effective_measurement_inputTextArea.getText());

            if ((measurement_value <= Integer.parseInt(Sim_App.min_effective_measurement_inputTextField.getText()))
                    && (remoteNode != currentNode.id)) {
                Sim_App.effective_remoteNodes.add(remoteNode);

                //System.out.println("Effective Node " + remoteNode + " added for " + currentNode + " due to measurement " + measurement_value);

                Sim_App.nodeID_to_nodeObject.get(remoteNode).cdl.update_Measurement_and_ExtentReach(measurement_value);
            }
        }
    }

    static private void sort_nodes_by_popularity(){
        // Create a Node-Popularity mapping (based on the average Beliefs-Strength from the k strongest measurements)
        HashMap<Integer, Double> node_popularity = new HashMap<>();

        for (Entry<Integer, Node> current_NodeEntry: Sim_App.nodeID_to_nodeObject.entrySet()) {
            int current_NodeID = current_NodeEntry.getKey();
            Node current_Node = current_NodeEntry.getValue();

            List<Double> measurement_values_list = new ArrayList<>(){};

            measurement_values_list.addAll(current_Node.measurement_from_node.values());

            // Keep only the 5 strongest signals
            Collections.sort(measurement_values_list);

            int considered_kNearestNeigbors_for_ClosenessCheck = Integer.parseInt(
                    Sim_App.kNearestNeighbours_for_BeliefsStrength_inputTextField.getText());

            if (measurement_values_list.size() > considered_kNearestNeigbors_for_ClosenessCheck){
                node_popularity.put(current_NodeID, getAverage(measurement_values_list.subList(0, considered_kNearestNeigbors_for_ClosenessCheck)));
            }
            else {
                node_popularity.put(current_NodeID, getAverage(measurement_values_list));
            }
        }

        Sim_App.OrderedByBeliefsStrength_NodeIDs = new ArrayList<>();

//        System.out.println(node_popularity);

        node_popularity.entrySet().stream()
                .sorted(HashMap.Entry.comparingByValue())
                .forEachOrdered(x -> Sim_App.OrderedByBeliefsStrength_NodeIDs.add(x.getKey()));

//        System.out.println(Sim_App.OrderedByBeliefsStrength_NodeIDs);
    }

    static private double getAverage(List <Double> items) {
        double sum = 0;
        if(!items.isEmpty()) {
            for (double mark: items) {
                sum += mark;
            }
            return sum/items.size();
        }
        return sum;
    }

    static private void constrainLongDistances(){
        // At this point we have considered all recorded pair-measurements.
        // However, we also need to consider all pairs for which no measurement exists. These relations shall be used
        // to constraint close distances
        for (Entry<Integer, Node> current_NodeEntry: Sim_App.nodeID_to_nodeObject.entrySet()) {
            int current_NodeID = current_NodeEntry.getKey();
            Node current_Node = current_NodeEntry.getValue();

            for (Entry<Integer, Node> remote_NodeEntry: Sim_App.nodeID_to_nodeObject.entrySet()) {
                int remote_NodeID = remote_NodeEntry.getKey();
                Node remote_Node = remote_NodeEntry.getValue();

                // Avoid considering the same Node
                if (current_NodeID != remote_NodeID){
                    //System.out.println(current_NodeID + " to " + remote_NodeID + ": " + );
                }
            }
        }
    }

    static private void computeInitialCrossDistances(){
        // At this point, we have already generated all involved Nodes

        // Update all the distances
        for (Entry<Integer, Node> current_NodeEntry: Sim_App.nodeID_to_nodeObject.entrySet()) {
            int current_NodeID = current_NodeEntry.getKey();
            Node current_Node = current_NodeEntry.getValue();

            for (Entry<Integer, Node> remote_NodeEntry: Sim_App.nodeID_to_nodeObject.entrySet()) {
                int remote_NodeID = remote_NodeEntry.getKey();
                Node remote_Node = remote_NodeEntry.getValue();

                // Avoid considering the same Node
                if(current_NodeID != remote_NodeID){
                    // Update for current Node,
                    // both the true and current (due to initial randomness) Distance towards the remote Node
                    double current_distance_to_remoteNode = current_Node.getDistanceToNode(remote_Node, false);
                    current_Node.current_distance_to_node.put(remote_NodeID, current_distance_to_remoteNode);

                    double true_distance_to_remoteNode = current_Node.getDistanceToNode(remote_Node, true);
                    current_Node.true_distance_to_node.put(remote_NodeID, true_distance_to_remoteNode);

                    //System.out.println(current_NodeID + ":[" + current_Node.true_relative_x + "," + current_Node.true_relative_y + "]- " + remote_NodeID + ":[" + remote_Node.true_relative_x + "," + remote_Node.true_relative_y + "]: DistanceToRemoteNode= " + current_distance_to_remoteNode);
                }
            }
        }
    }

    static private void parse_db() throws Exception {
        // Loading the database
        Sim_App.append_to_text_area("Parsing Node DB");

        // Open the file
        FileInputStream fstream = new FileInputStream(Sim_App.input_file_path);
        BufferedReader br = new BufferedReader(new InputStreamReader(fstream));

        String strLine;

        // Data format in the .rss file is important!
        String positions_header = "#POSITIONS GROUND TRUTH#";
        String rss_header = "#RSS_" + Sim_App.current_eval_iteration + "#";

        String current_parsing_type = null;

        //Read File Line By Line
        while ((strLine = br.readLine()) != null)   {

            // Try to detect a flag
            if (strLine.equals(positions_header)){
                current_parsing_type = positions_header;
                continue;
            }
            else if (strLine.equals(rss_header)){
                current_parsing_type = rss_header;
                continue;
            }
            else if (strLine.equals("")){
                current_parsing_type = null;
                continue;
            }

            if (current_parsing_type != null){
                // Being here means that we haven't escaped above with a continue due to successful header_check matching
                // Handle accordingly the parsed data
                if (current_parsing_type.equals(positions_header)){
                    // Start with the position
                    String[] position_parts = strLine.split(":");
                    String[] coords = position_parts[1].split(";");

                    int parsed_nodeID = Integer.parseInt(position_parts[0].trim());
                    double posX = Double.parseDouble(coords[0].trim());
                    double posY = Double.parseDouble(coords[1].trim());

                    // Create the Node object and add it to the Node Map
                    Node new_node = new Node(parsed_nodeID, posX, posY);
                    Sim_App.nodeID_to_nodeObject.put(parsed_nodeID, new_node);
                    Sim_App.append_to_text_area(new_node.get_report());
                }

                else {
                    String[] measurement_value_parts = strLine.split(":");

                    String[] str_nodes = measurement_value_parts[0].split(";");
                    int nodeA = Integer.parseInt(str_nodes[0]);
                    int nodeB = Integer.parseInt(str_nodes[1]);

                    double measurement_value = Double.parseDouble(measurement_value_parts[1].split("&")[0]);

                    // Update for 1st Node, the RSS towards the 2nd Node
                    Sim_App.nodeID_to_nodeObject.get(nodeA).measurement_from_node.put(nodeB, measurement_value);

                    //System.out.println("Node " + nodeA + " to Node " + nodeB + " measurement: " + measurement_value);
                }
            }
        }

        //Close the input stream
        fstream.close();
    }

    static void resume_SwarmPositioning(){
        Sim_App.optimization_running = true;

        Sim_App.append_to_text_area("Position Estimations:");

        // Check if there is no remaining step from previous unfinished cycles
        if (Sim_App.temp_OrderedRemoteNodeIDs.size()==0){

            if (Sim_App.headless_mode || Sim_App.rss_density_check_btn.getState()){
                // We are starting a new Cycle. So, we need to align the swarm based on the principal spatial variation
                //MathEngine.align_Swarm();
                Sim_App.temp_OrderedRemoteNodeIDs.addAll(Sim_App.OrderedByBeliefsStrength_NodeIDs);
            }
            else{
                // We are starting a new Cycle. So, we need to align the swarm based on the principal spatial variation
                MathEngine.align_Swarm();

                // In case we have set the Orientation indexing, we need to sort the Nodes according to their X value
                Sim_App.OrderedByLastCycleOrientation_NodeIDs = MathEngine.order_NodeIDs_byPositionX();
                Sim_App.temp_OrderedRemoteNodeIDs.addAll(Sim_App.OrderedByLastCycleOrientation_NodeIDs);
            }

            // Update also the progress counters
            Sim_App.cycleCounter = Sim_App.cycleCounter + 1;
            Sim_App.stepCounter = 0;
        }
        // Check if the user wants to get results per step
        if (!Sim_App.headless_mode && Sim_App.results_per_step_btn.getState()){
            Sim_App.stepCounter = Sim_App.stepCounter + 1;

            Node currentNode = Sim_App.nodeID_to_nodeObject.get(Sim_App.temp_OrderedRemoteNodeIDs.remove(0));
            //System.out.println("Removing: " + currentNode + " TempList: " + RemoteNodeIDbyPopularity_tracker.size() + " OriginalList: " + NodeIDbyPopularity_originalList.size());

            //currentNode = 6; // Set this manually for debugging purposes

            // Let Java calculate the most probable position of current Node and use the outcome to update the Node
            // Since we might end up with precision problems due to many probability multiplications,
            // we can do this more accurately with Mathematica. Yet, for the moment, we handle this problem by
            // regulating the maximum RSS that we are considering during the positioning steps

            double[] new_current_position = MathEngine.find_BestPosition_ForCurrentNode(currentNode, Sim_App.cycleCounter, Sim_App.stepCounter); // Java

            if (new_current_position != null){
                currentNode.update_CurrentNodePos(new_current_position[0], new_current_position[1]);
            }

            MapField.update_MapExtent();
            MathEngine.publish_results(Sim_App.cycleCounter, Sim_App.stepCounter, currentNode);

            // todo use this for debugging whenever needed
            /*
            if (resetAll_CurrentNodePos_to_TruePos){
                reset_CurrentNodePos_to_TruePos();
            }
            */
        }
        // Being here means that the user wants to get results per cycle
        else {
            boolean last_step = false;
            int remaining_steps = Sim_App.temp_OrderedRemoteNodeIDs.size();

            for (int step = 0; step<remaining_steps; step++){
                Sim_App.stepCounter = Sim_App.stepCounter + 1;

                int currentNodeID = Sim_App.temp_OrderedRemoteNodeIDs.remove(0);
                Node currentNode = Sim_App.nodeID_to_nodeObject.get(currentNodeID);

                // Check if after removing this node, we ended up at the last optimization step
                if (Sim_App.temp_OrderedRemoteNodeIDs.size()==0){
                    last_step = true;
                }

                //System.out.println("Removing: " + currentNodeID + " TempList: " + RemoteNodeIDbyPopularity_tracker.size() + " OriginalList: " + NodeIDbyPopularity_originalList.size());

                // Let Java calculate the most probable position of current Node and use the outcome to update the Node
                // Since we might end up with precision problems due to many probability multiplications,
                // we can do this more accurately with Mathematica. Yet, for the moment, we handle this problem by
                // regulating the maximum RSS that we are considering during the positioning steps

                double[] new_current_position = MathEngine.find_BestPosition_ForCurrentNode(
                        Sim_App.nodeID_to_nodeObject.get(currentNodeID), Sim_App.cycleCounter, Sim_App.stepCounter);

                if (new_current_position != null){
                    currentNode.update_CurrentNodePos(new_current_position[0], new_current_position[1]);
                }

                MapField.update_MapExtent();
                // Check whether we are currently at the last step
                if (last_step){
                    MathEngine.publish_results(Sim_App.cycleCounter, Sim_App.stepCounter, currentNode);
                }

                // Check if the stop Button is not enabled.
                // In such case, the user has manually stopped the optimization and so, break the iteration..
                if (!Sim_App.stopBtn.isEnabled() || Sim_App.optimization_cycles < Sim_App.cycleCounter){
                    System.out.println("Current finished cycle: " + Sim_App.optimization_cycles);
                    break;
                }
            }
        }

        Sim_App.optimization_running = false;
        Sim_App.append_to_text_area("Map Extent: (" + MapField.global_minPlotX + ", " + MapField.global_maxPlotX + "), (" + MapField.global_minPlotY + ", " + MapField.global_maxPlotY + ")");
        Sim_App.append_to_text_area("=========== Optimization Finished ===========");

        // If we are running in headless mode and the cycles have finished,
        // we should stop nicely the current optimization process as we would do in GUI mode by pressing the Stop
        if (Sim_App.headless_mode && Sim_App.optimization_cycles <= Sim_App.cycleCounter){
            // Stop the optimization right after the chosen amount of cycles
            Sim_App.stop_optimization();

            // Stop the auto-resumer for the current optimization process
            Sim_App.scheduled_auto_resumer.cancel(true);
            Sim_App.scheduler.shutdown();
        }
    }

    // Use the following to reset everytime the Nodes to their True Position (for debugging)
    static private void reset_CurrentNodePos_to_TruePos(){
        // Loop throughout all Nodes
        for (Node node: Sim_App.nodeID_to_nodeObject.values()){
            node.update_CurrentNodePos(node.true_relative_x, node.true_relative_y);
        }
    }
}
