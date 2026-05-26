using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace PouleLabApp.API.Migrations
{
    /// <inheritdoc />
    public partial class FreeTextAnalysisTypes : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropForeignKey(
                name: "FK_AnalysisResults_AnalysisTypes_AnalysisTypeId",
                table: "AnalysisResults");

            migrationBuilder.DropTable(
                name: "AnalysisTypes");

            migrationBuilder.DropIndex(
                name: "IX_AnalysisResults_AnalysisTypeId",
                table: "AnalysisResults");

            migrationBuilder.DropColumn(
                name: "AnalysisTypeId",
                table: "AnalysisResults");

            migrationBuilder.AlterColumn<string>(
                name: "RecordedById",
                table: "AnalysisResults",
                type: "nvarchar(450)",
                nullable: true,
                oldClrType: typeof(string),
                oldType: "nvarchar(450)");

            migrationBuilder.AddColumn<string>(
                name: "AnalysisName",
                table: "AnalysisResults",
                type: "nvarchar(max)",
                nullable: false,
                defaultValue: "");

            migrationBuilder.AddColumn<string>(
                name: "Unit",
                table: "AnalysisResults",
                type: "nvarchar(max)",
                nullable: false,
                defaultValue: "");
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropColumn(
                name: "AnalysisName",
                table: "AnalysisResults");

            migrationBuilder.DropColumn(
                name: "Unit",
                table: "AnalysisResults");

            migrationBuilder.AlterColumn<string>(
                name: "RecordedById",
                table: "AnalysisResults",
                type: "nvarchar(450)",
                nullable: false,
                defaultValue: "",
                oldClrType: typeof(string),
                oldType: "nvarchar(450)",
                oldNullable: true);

            migrationBuilder.AddColumn<int>(
                name: "AnalysisTypeId",
                table: "AnalysisResults",
                type: "int",
                nullable: false,
                defaultValue: 0);

            migrationBuilder.CreateTable(
                name: "AnalysisTypes",
                columns: table => new
                {
                    Id = table.Column<int>(type: "int", nullable: false)
                        .Annotation("SqlServer:Identity", "1, 1"),
                    Description = table.Column<string>(type: "nvarchar(max)", nullable: false),
                    Name = table.Column<string>(type: "nvarchar(max)", nullable: false),
                    ReferenceMax = table.Column<double>(type: "float", nullable: false),
                    ReferenceMin = table.Column<double>(type: "float", nullable: false),
                    Unit = table.Column<string>(type: "nvarchar(max)", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_AnalysisTypes", x => x.Id);
                });

            migrationBuilder.CreateIndex(
                name: "IX_AnalysisResults_AnalysisTypeId",
                table: "AnalysisResults",
                column: "AnalysisTypeId");

            migrationBuilder.AddForeignKey(
                name: "FK_AnalysisResults_AnalysisTypes_AnalysisTypeId",
                table: "AnalysisResults",
                column: "AnalysisTypeId",
                principalTable: "AnalysisTypes",
                principalColumn: "Id",
                onDelete: ReferentialAction.Cascade);
        }
    }
}
