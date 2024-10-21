
nodes = []
positions = []

with open("Export/MS/BLE/T_1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21_20/0/results.log", "r") as log_data:
    for line in log_data:
        node_info = line.split(";")
        node_id = node_info[0]
        x, y = map(float, node_info[1].split(":"))
        nodes.append(node_id)
        positions.append([x, y])
        
# Extract x and y coordinates
x_values = [pos[0] for pos in positions]
y_values = [pos[1] for pos in positions]

from matplotlib import pyplot as plt
# Plotting the node positions
plt.figure(figsize=(10, 6))
plt.scatter(x_values, y_values, color='blue')

# Annotating each node with its number
for i, (x, y) in enumerate(positions):
    plt.annotate(nodes[i], (x, y), textcoords="offset points", xytext=(0, 10), ha='center')

# Adding grid, title, and axis labels
plt.grid(True)
plt.title('Node Positions Visualization')
plt.xlabel('X Coordinate')
plt.ylabel('Y Coordinate')

# Show the plot
plt.savefig("Node_Positions_Visualization.png")