class Cell {
    constructor(x, y) {
        this.x = x;
        this.y = y;
        this.isObstacle = false;
        this.color = 'white';
        this.parent = null;
        this.weight = 1;
    }

    draw(ctx) {
        ctx.strokeStyle = 'black';
        ctx.strokeRect(this.x * cellSize, this.y * cellSize, cellSize, cellSize);
        if (this.isObstacle) {
            ctx.fillStyle = 'gray';
            ctx.fillRect(this.x * cellSize, this.y * cellSize, cellSize, cellSize);
        }
    }
}

function createCellGrid(rows, cols) {
    const grid = [];
    for (let r = 0; r < rows; r++) {
        const row = [];
        for (let c = 0; c < cols; c++) {
            row.push(new Cell(c, r));
        }
        grid.push(row);
    }
    return grid;
}

export { Cell, createCellGrid };