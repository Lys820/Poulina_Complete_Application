using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace PouleLabApp.API.Migrations
{
    /// <inheritdoc />
    public partial class AddSampleIdToDeadline : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.AddColumn<int>(
                name: "SampleId",
                table: "Deadlines",
                type: "int",
                nullable: true);

            migrationBuilder.CreateIndex(
                name: "IX_Deadlines_SampleId",
                table: "Deadlines",
                column: "SampleId");

            migrationBuilder.AddForeignKey(
                name: "FK_Deadlines_Samples_SampleId",
                table: "Deadlines",
                column: "SampleId",
                principalTable: "Samples",
                principalColumn: "Id");
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropForeignKey(
                name: "FK_Deadlines_Samples_SampleId",
                table: "Deadlines");

            migrationBuilder.DropIndex(
                name: "IX_Deadlines_SampleId",
                table: "Deadlines");

            migrationBuilder.DropColumn(
                name: "SampleId",
                table: "Deadlines");
        }
    }
}
