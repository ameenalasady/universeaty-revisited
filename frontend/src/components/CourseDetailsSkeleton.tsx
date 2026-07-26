import React from "react";
import {
  Card,
  CardContent,
  CardFooter,
  CardHeader,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Separator } from "@/components/ui/separator";

const CourseDetailsSkeleton: React.FC = () => (
  <Card className="mt-6 border-border/40 bg-card/30 backdrop-blur-sm overflow-hidden flex flex-col gap-0 py-0 animate-pulse">
    <CardHeader className="px-4 sm:px-6 pt-6 pb-4">
      <Skeleton className="h-8 w-2/5 mb-2 rounded" />
      <Skeleton className="h-4 w-4/5 rounded" />
    </CardHeader>
    <CardContent className="space-y-8 px-4 sm:px-6 pb-8">
      {/* Stats Panel */}
      <div className="mb-6 border border-border/40 bg-muted/20 rounded-xl p-4">
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
      <div className="bg-muted/20 border border-border/40 p-4 rounded-xl flex flex-col sm:flex-row items-center justify-between gap-4">
        <div className="text-center sm:text-left flex flex-col gap-1">
          <Skeleton className="h-6 w-40" />
          <Skeleton className="h-4 w-56" />
        </div>
        <Skeleton className="h-12 w-40 rounded-md" />
      </div>

      {/* History Range Selector */}
      <div className="flex items-center justify-end gap-2 -mt-4">
        <Skeleton className="h-3.5 w-3.5 rounded-full" />
        <Skeleton className="h-3 w-20" />
        <Skeleton className="h-7 w-[110px] rounded-md" />
      </div>

      {/* Section Blocks */}
      <div className="space-y-12">
        {[1, 2].map((blockIndex) => (
          <div key={`skeleton-block-${blockIndex}`} className="space-y-4">
            <div className="flex items-center justify-between">
              <Skeleton className="h-5 w-24" />
              <Skeleton className="h-4 w-16 md:hidden" />
            </div>

            {/* Desktop Table */}
            <div className="hidden md:block">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-[100px]">
                      <Skeleton className="h-4 w-16 rounded" />
                    </TableHead>
                    <TableHead className="text-center w-[140px]">
                      <Skeleton className="h-4 w-24 mx-auto rounded" />
                    </TableHead>
                    <TableHead className="text-right w-[100px]">
                      <Skeleton className="h-4 w-12 ml-auto rounded" />
                    </TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {[1, 2, 3].map((rowIndex) => (
                    <TableRow key={`skeleton-row-${blockIndex}-${rowIndex}`}>
                      <TableCell>
                        <Skeleton className="h-5 w-full rounded" />
                      </TableCell>
                      <TableCell className="text-center">
                        <Skeleton className="h-5 w-20 mx-auto rounded-md" />
                      </TableCell>
                      <TableCell className="text-right">
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
              <div className="grid grid-cols-1 gap-4">
                {[1, 2, 3].map((cardIndex) => (
                  <Skeleton
                    key={`skeleton-card-${blockIndex}-${cardIndex}`}
                    className="h-24 w-full rounded-xl"
                  />
                ))}
              </div>
            </div>

            {blockIndex < 2 && (
              <Separator className="my-10 border-border/40" />
            )}
          </div>
        ))}
      </div>
    </CardContent>
    <CardFooter className="text-xs sm:text-sm border-t border-border/30 bg-muted/20 px-4 py-5 sm:px-6 m-0 w-full rounded-none">
      <div className="flex gap-3">
        <Skeleton className="h-5 w-5 shrink-0 rounded" />
        <div className="flex-1 space-y-2">
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-4/5" />
        </div>
      </div>
    </CardFooter>
  </Card>
);

export default CourseDetailsSkeleton;
