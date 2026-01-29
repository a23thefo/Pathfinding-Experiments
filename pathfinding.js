let grid = [];
const rows = 25;
const cols = 40;
const cellSize = 30;
const canvas = document.getElementById('pathfindingCanvas');
const ctx = canvas.getContext('2d');

function setupGrid() {
    for (let r = 0; r < rows; r++) {
        grid[r] = [];
        for (let c = 0; c < cols; c++) {
            grid[r][c] = 0; // 0 represents walkable cell
        }
    }
    canvas.width = cols * cellSize;
    canvas.height = rows * cellSize;
}

function drawGrid(ctx) {
    for (let r = 0; r < rows; r++) {
        for (let c = 0; c < cols; c++) {
            ctx.strokeStyle = 'black';
            ctx.strokeRect(c * cellSize, r * cellSize, cellSize, cellSize);
            if (grid[r][c] === 1) { // 1 represents obstacle
                ctx.fillStyle = 'gray';
                ctx.fillRect(c * cellSize, r * cellSize, cellSize, cellSize);
            }
        }
    }
}
setupGrid();
drawGrid(ctx);
