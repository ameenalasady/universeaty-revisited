import React from "react";
import { Card, CardContent, CardFooter, CardHeader } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

const CourseDetailsSkeleton: React.FC = () => (
  <Card className="border-border/50 bg-card/40 backdrop-blur-sm overflow-hidden flex flex-col gap-0 py-0 shadow-sm">
    <CardHeader className="px-4 sm:px-6 pt-6 pb-5 border-b border-border/40">
      <div className="flex items-center gap-3 mb-2">
        <Skeleton className="h-8 w-2/5 rounded" />
        <Skeleton className="h-6 w-24 rounded-md" />
      </div>
      <Skeleton className="h-4 w-1/3 mb-1 rounded" />
      <Skeleton className="h-4 w-4/5 rounded" />
      <div className="flex flex-wrap gap-2 mt-3">
        <Skeleton className="h-6 w-24 rounded-md" />
        <Skeleton className="h-6 w-36 rounded-md" />
      </div>
    </CardHeader>
    <CardContent className="space-y-6 px-4 sm:px-6 py-6">
      {/* Stats Panel */}
      <div className="border border-border/50 bg-muted/20 rounded-xl backdrop-blur-sm p-4">
        <div className="flex flex-col gap-6 sm:flex-row sm:items-center sm:justify-between sm:gap-4">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:gap-8">
            <div className="flex items-center gap-3">
              <Skeleton className="h-9 w-9 rounded-lg" />
              <div className="flex flex-col gap-1">
                <Skeleton className="h-5 w-10" />
                <Skeleton className="h-4 w-24" />
              </div>
            </div>
            <Skeleton className="h-7 w-28 rounded-md" />
          </div>
          <div className="flex flex-col gap-2 sm:items-end">
            <Skeleton className="h-3 w-28" />
            <div className="flex flex-wrap gap-2 sm:justify-end">
              <Skeleton className="h-6 w-20 rounded-md" />
              <Skeleton className="h-6 w-20 rounded-md" />
              <Skeleton className="h-6 w-20 rounded-md" />
            </div>
          </div>
        </div>
      </div>

      {/* Batch Watch Block */}
      <div className="bg-muted/20 border border-border/50 p-4 sm:p-5 rounded-xl flex flex-col sm:flex-row items-center justify-between gap-4">
        <div className="text-center sm:text-left flex flex-col gap-1">
          <Skeleton className="h-6 w-40" />
          <Skeleton className="h-4 w-56" />
        </div>
        <Skeleton className="h-11 w-40 rounded-lg" />
      </div>

      {/* History Range Selector */}
      <div className="flex items-center justify-between gap-3 border-t border-border/40 pt-5">
        <Skeleton className="h-4 w-32" />
        <Skeleton className="h-9 w-[130px] rounded-lg" />
      </div>

      {/* Section Blocks — single shared table layout to match real UI */}
      <div className="space-y-10">
        {[1, 2].map((blockIndex) => (
          <div key={`skeleton-block-${blockIndex}`} className="space-y-3">
            <div className="flex items-center gap-2.5">
              <Skeleton className="h-5 w-24" />
              <Skeleton className="h-5 w-8 rounded-md" />
            </div>

            {/* Desktop Table */}
            <div className="hidden md:block overflow-hidden rounded-xl border border-border/50">
              <Table>
                <TableHeader>
                  <TableRow className="border-border/50 bg-muted/30 hover:bg-muted/30">
                    <TableHead className="h-10 w-[45%] pl-4">
                      <Skeleton className="h-3.5 w-16 rounded" />
                    </TableHead>
                    <TableHead className="h-10 w-[30%]">
                      <Skeleton className="h-3.5 w-24 mx-auto rounded" />
                    </TableHead>
                    <TableHead className="h-10 w-[25%] pr-4">
                      <Skeleton className="h-3.5 w-12 ml-auto rounded" />
                    </TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {[1, 2, 3].map((rowIndex) => (
                    <TableRow
                      key={`skeleton-row-${blockIndex}-${rowIndex}`}
                      className="border-border/40"
                    >
                      <TableCell className="py-3.5 pl-4 font-medium">
                        <div className="flex flex-col gap-1.5">
                          <Skeleton className="h-4 w-8 rounded" />
                          <Skeleton className="h-3 w-32 rounded" />
                        </div>
                      </TableCell>
                      <TableCell className="py-3.5 text-center">
                        <Skeleton className="h-6 w-24 mx-auto rounded-md" />
                      </TableCell>
                      <TableCell className="py-3.5 pr-4 text-right">
                        <div className="flex items-center justify-end gap-1">
                          <Skeleton className="h-8 w-8 rounded-lg" />
                          <Skeleton className="h-8 w-8 rounded-lg" />
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>

            {/* Mobile Cards */}
            <div className="md:hidden">
              <div className="grid grid-cols-1 gap-3">
                {[1, 2, 3].map((cardIndex) => (
                  <div
                    key={`skeleton-card-${blockIndex}-${cardIndex}`}
                    className="border rounded-xl overflow-hidden bg-card/40 backdrop-blur-sm border-border/50 shadow-sm p-4 flex flex-col gap-3"
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex flex-col gap-1">
                        <Skeleton className="h-6 w-12" />
                        <Skeleton className="h-3 w-24" />
                      </div>
                      <div className="flex flex-col items-end gap-1">
                        <Skeleton className="h-6 w-20 rounded-md" />
                        <Skeleton className="h-3 w-16" />
                      </div>
                    </div>
                    <div className="flex flex-wrap items-center gap-1.5">
                      <Skeleton className="h-4 w-32" />
                      <Skeleton className="h-4 w-14 rounded-md" />
                    </div>
                    <div className="flex items-center gap-2">
                      <Skeleton className="h-11 flex-1 rounded-lg" />
                      <Skeleton className="h-11 w-11 rounded-lg" />
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {blockIndex < 2 && <div className="border-b border-border/40 pt-7" />}
          </div>
        ))}
      </div>
    </CardContent>
    <CardFooter className="text-xs sm:text-sm text-muted-foreground border-t border-border/40 bg-muted/20 px-4 py-4 sm:px-6 m-0 w-full">
      <div className="flex gap-3">
        <Skeleton className="h-4 w-4 shrink-0 rounded" />
        <div className="flex-1">
          <Skeleton className="h-4 w-full" />
        </div>
      </div>
    </CardFooter>
  </Card>
);

export default CourseDetailsSkeleton;
