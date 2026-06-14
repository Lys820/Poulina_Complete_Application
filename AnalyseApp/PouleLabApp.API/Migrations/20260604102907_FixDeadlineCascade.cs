using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace PouleLabApp.API.Migrations
{
    /// <inheritdoc />
    public partial class FixDeadlineCascade : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropForeignKey(
                name: "FK_Deadlines_Samples_SampleId",
                table: "Deadlines");

            migrationBuilder.AddForeignKey(
                name: "FK_Deadlines_Samples_SampleId",
                table: "Deadlines",
                column: "SampleId",
                principalTable: "Samples",
                principalColumn: "Id",
                onDelete: ReferentialAction.Restrict);
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropForeignKey(
                name: "FK_Deadlines_Samples_SampleId",
                table: "Deadlines");

            migrationBuilder.AddForeignKey(
                name: "FK_Deadlines_Samples_SampleId",
                table: "Deadlines",
                column: "SampleId",
                principalTable: "Samples",
                principalColumn: "Id",
                onDelete: ReferentialAction.Cascade);
        }
    }
}
