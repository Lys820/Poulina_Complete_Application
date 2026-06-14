using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace PouleLabApp.API.Migrations
{
    /// <inheritdoc />
    public partial class MakeNotificationRequestIdNullable : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropForeignKey(
                name: "FK_Notifications_AnalysisRequests_RequestId",
                table: "Notifications");

            migrationBuilder.AlterColumn<int>(
                name: "RequestId",
                table: "Notifications",
                type: "int",
                nullable: true,
                oldClrType: typeof(int),
                oldType: "int");

            

            

            

            migrationBuilder.AddForeignKey(
                name: "FK_Notifications_AnalysisRequests_RequestId",
                table: "Notifications",
                column: "RequestId",
                principalTable: "AnalysisRequests",
                principalColumn: "Id");
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {

            migrationBuilder.DropForeignKey(
                name: "FK_Notifications_AnalysisRequests_RequestId",
                table: "Notifications");

            migrationBuilder.AlterColumn<int>(
                name: "RequestId",
                table: "Notifications",
                type: "int",
                nullable: false,
                defaultValue: 0,
                oldClrType: typeof(int),
                oldType: "int",
                oldNullable: true);

            migrationBuilder.AddForeignKey(
                name: "FK_Notifications_AnalysisRequests_RequestId",
                table: "Notifications",
                column: "RequestId",
                principalTable: "AnalysisRequests",
                principalColumn: "Id",
                onDelete: ReferentialAction.Cascade);
        }
    }
}
